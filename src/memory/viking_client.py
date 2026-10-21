"""OpenViking memory client for parallax.observer.

Talks to the OpenViking 0.5 server over HTTP with the official SDK. The
server owns the storage, the embeddings and the vector index, this module is
the thin layer the application uses.

Two tiers live under viking://resources:

    knowledge/    the source text, verbatim, citable
    enrichment/   the ammunition: catchphrases, quotes, misleading claims

Every tier file is reachable three ways:

    abstract(uri)   the L0 essence, 50 to 150 words
    overview(uri)   the L1 insight, a few hundred words
    read(uri)       the L2 content, the full text

Searches are scoped to a worldview, so the agent can be told which universe
it is arguing from and only ever sees that universe.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from openviking_sdk import SyncHTTPClient

logger = logging.getLogger(__name__)

DEFAULT_SERVER = os.environ.get("OPENVIKING_URL", "http://localhost:1933")
DEFAULT_USER = os.environ.get("OPENVIKING_USER", "default")
DEFAULT_TIER = "knowledge"

# where the application keeps its own session state
DEFAULT_PROFILE_DIR = Path(
    os.environ.get("OPENVIKING_PROFILE_DIR", "memory/openviking/user")
)

BELIEF_OPPOSITES = {
    "flat-earth": "spherical-earth",
    "spherical-earth": "flat-earth",
    "discworld": "spherical-earth",
    "norse": "spherical-earth",
}


class VikingClient:
    """Semantic search, tiered content access and session memory.

    Attributes:
        server: OpenViking server URL
        user: Account the client acts as
        tier: Default tier, "knowledge" or "enrichment"
    """

    def __init__(
        self,
        server: str = DEFAULT_SERVER,
        user: str = DEFAULT_USER,
        tier: str = DEFAULT_TIER,
        profile_dir: Path = DEFAULT_PROFILE_DIR,
        timeout: float = 120.0,
    ) -> None:
        self.server = server
        self.user = user
        self.tier = tier
        self.profile_dir = Path(profile_dir)

        self._client = SyncHTTPClient(
            url=server, api_key="", user=user, timeout=timeout
        )
        self._client.initialize()

        logger.info("VikingClient ready: server=%s tier=%s", server, tier)

    # ------------------------------------------------------------------
    # URIs
    # ------------------------------------------------------------------

    def tier_uri(self, tier: str | None = None) -> str:
        """Root URI of a tier."""
        return f"viking://resources/{tier or self.tier}"

    def wisdom_uri(
        self,
        name: str,
        target: str | None = None,
        category: str | None = None,
        tier: str | None = None,
    ) -> str:
        """URI of one wisdom."""
        parts = [self.tier_uri(tier)]
        if target:
            parts.append(target)
        if category:
            parts.append(category)
        parts.append(name)
        return "/".join(parts)

    def scope_uri(
        self,
        target: str | None = None,
        category: str | None = None,
        tier: str | None = None,
    ) -> str:
        """URI of a subtree, used to scope a search."""
        parts = [self.tier_uri(tier)]
        if target:
            parts.append(target)
        if category:
            parts.append(category)
        return "/".join(parts)

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        target: str | None = None,
        category: str | None = None,
        top_k: int = 5,
        tier: str | None = None,
        level: int | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search inside one worldview.

        Args:
            query: What to look for
            target: Worldview filter, for example "flat-earth"
            category: Category filter, for example "catchphrases"
            top_k: How many hits to return
            tier: "knowledge" or "enrichment"
            level: Restrict to a tier, 0 for L0, 1 for L1, 2 for L2

        Returns:
            One dict per hit with uri, score, level and abstract
        """
        options: dict[str, Any] = {"include_provenance": True}
        if level is not None:
            options["level"] = level

        result = self._client.find(
            query=query,
            target_uri=self.scope_uri(target, category, tier),
            limit=top_k,
            options=options,
        )

        hits: list[dict[str, Any]] = []
        for hit in result.get("resources", []):
            hits.append(
                {
                    "uri": hit.get("uri", ""),
                    "score": hit.get("score", 0.0),
                    "level": hit.get("level"),
                    "abstract": hit.get("abstract", ""),
                    "context_type": hit.get("context_type", ""),
                    "chunk_name": hit.get("chunk_name", ""),
                    "target": hit.get("target", ""),
                    "category": hit.get("category", ""),
                }
            )

        logger.debug("search %r in %s -> %d hits", query, target, len(hits))
        return hits

    def search_context(
        self,
        query: str,
        target: str | None = None,
        category: str | None = None,
        top_k: int = 5,
        tier: str | None = None,
        token_budget: int = 4000,
    ) -> dict[str, Any]:
        """Search and get the assembled context in one call.

        This is the form the agents want: one call, one blob of text that
        already has the right wisdoms in it.
        """
        result = self._client.search_context(
            query=query,
            target_uri=self.scope_uri(target, category, tier),
            limit=top_k,
        )
        return {
            "context": getattr(result, "context", "") or "",
            "resources": getattr(result, "resources", []) or [],
            "usage": getattr(result, "usage", {}) or {},
        }

    # ------------------------------------------------------------------
    # TIERED CONTENT
    # ------------------------------------------------------------------

    def get_abstract(self, uri: str) -> str:
        """L0 essence of a wisdom."""
        return self._client.abstract(uri)

    def get_overview(self, uri: str) -> str:
        """L1 insight of a wisdom."""
        return self._client.overview(uri)

    def get_content(self, uri: str) -> str:
        """L2 content of a wisdom.

        The URI points at the wisdom folder, so the content file is derived.
        """
        base = uri.rstrip("/")
        if base.endswith(".md"):
            return self._client.read(base)
        return self._client.read(f"{base}/content.md")

    def read_wisdom(self, uri: str) -> dict[str, str]:
        """All three tiers of a wisdom in one dict."""
        return {
            "uri": uri,
            "l0_abstract": self.get_abstract(uri),
            "l1_overview": self.get_overview(uri),
            "l2_content": self.get_content(uri),
        }

    # ------------------------------------------------------------------
    # LISTING
    # ------------------------------------------------------------------

    def _ls(self, uri: str) -> list[dict[str, Any]]:
        """The entries under a URI.

        The SDK returns a plain list, but an older shape was a dict with an
        entries key, so both are handled.
        """
        result = self._client.ls(uri)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("entries", []) or result.get("items", [])
        return []

    def list_targets(self, tier: str | None = None) -> list[str]:
        """The worldviews in a tier."""
        return [
            entry["name"]
            for entry in self._ls(self.tier_uri(tier))
            if entry.get("isDir")
        ]

    def list_categories(self, target: str, tier: str | None = None) -> list[str]:
        """The categories in one worldview."""
        return [
            entry["name"]
            for entry in self._ls(self.scope_uri(target, tier=tier))
            if entry.get("isDir")
        ]

    def list_wisdoms(
        self,
        target: str,
        category: str,
        tier: str | None = None,
    ) -> list[str]:
        """The wisdom names in one category."""
        return [
            entry["name"]
            for entry in self._ls(self.scope_uri(target, category, tier))
            if entry.get("isDir")
        ]

    def count_wisdoms(
        self,
        target: str | None = None,
        category: str | None = None,
        tier: str | None = None,
    ) -> int:
        """How many wisdoms are in scope."""
        if target and category:
            return len(self.list_wisdoms(target, category, tier))
        if target:
            return sum(
                len(self.list_wisdoms(target, cat, tier))
                for cat in self.list_categories(target, tier)
            )
        return sum(
            self.count_wisdoms(t, tier=tier) for t in self.list_targets(tier)
        )

    # ------------------------------------------------------------------
    # SESSIONS
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        alterego: str,
        belief: str,
        persuasion_goal: str | None = None,
    ) -> Path:
        """Start a session and record the profile.

        The profile files are the application's own state, they live next to
        the server workspace. The conversation itself goes into an OpenViking
        session, so the server can extract memories from it.
        """
        profile_dir = self.profile_dir / session_id / "profile"
        memory_dir = self.profile_dir / session_id / "memory"
        profile_dir.mkdir(parents=True, exist_ok=True)
        memory_dir.mkdir(parents=True, exist_ok=True)

        if persuasion_goal is None:
            persuasion_goal = self.opposite_belief(belief)

        (profile_dir / "alterego-name.md").write_text(alterego)
        (profile_dir / "target-belief.md").write_text(belief)
        (profile_dir / "persuasion-goal.md").write_text(persuasion_goal)
        (memory_dir / "arguments-that-worked.md").write_text("")
        (memory_dir / "arguments-rejected.md").write_text("")

        try:
            self._client.create_session(session_id)
            self._client.add_message(
                session_id,
                "system",
                f"The user calls themselves {alterego}. "
                f"They believe the Earth is {belief}. "
                f"The goal is to persuade them toward {persuasion_goal}.",
            )
        except Exception as exc:
            logger.warning("OpenViking session %s not created: %s", session_id, exc)

        logger.info(
            "Session created: %s alterego=%r belief=%s goal=%s",
            session_id,
            alterego,
            belief,
            persuasion_goal,
        )
        return self.profile_dir / session_id

    def _profile_file(self, session_id: str, name: str) -> Path:
        return self.profile_dir / session_id / "profile" / name

    def get_user_belief(self, session_id: str) -> str:
        """What the user believes."""
        path = self._profile_file(session_id, "target-belief.md")
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        return path.read_text().strip()

    def get_persuasion_goal(self, session_id: str) -> str:
        """What we are trying to persuade the user toward."""
        path = self._profile_file(session_id, "persuasion-goal.md")
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        return path.read_text().strip()

    def record_argument(
        self,
        session_id: str,
        argument: str,
        success: bool,
        wisdom_uri: str | None = None,
    ) -> None:
        """Record an argument and whether it landed.

        The ledger stays on disk so it can be shown to the reader, and the
        argument also goes into the OpenViking session so the server can
        learn from it.
        """
        name = "arguments-that-worked.md" if success else "arguments-rejected.md"
        path = self.profile_dir / session_id / "memory" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("")

        entry = f"\n## {datetime.now().isoformat()}\n{argument}"
        if wisdom_uri:
            entry += f"\nSource: {wisdom_uri}"
        entry += "\n"

        with open(path, "a") as handle:
            handle.write(entry)

        try:
            self._client.add_message(session_id, "assistant", argument)
        except Exception as exc:
            logger.warning("Could not record the argument in the session: %s", exc)

        logger.info(
            "Argument recorded: session=%s success=%s preview=%r",
            session_id,
            success,
            argument[:60],
        )

    def _arguments(self, session_id: str, name: str) -> list[str]:
        path = self.profile_dir / session_id / "memory" / name
        if not path.exists():
            return []
        content = path.read_text().strip()
        if not content:
            return []
        return [part.strip() for part in content.split("##") if part.strip()]

    def get_arguments_that_worked(self, session_id: str) -> list[str]:
        """Arguments the user responded to."""
        return self._arguments(session_id, "arguments-that-worked.md")

    def get_arguments_rejected(self, session_id: str) -> list[str]:
        """Arguments the user pushed back on."""
        return self._arguments(session_id, "arguments-rejected.md")

    def commit_session(self, session_id: str, keep_recent_count: int = 2) -> None:
        """Let the server extract memories from the session."""
        try:
            self._client.commit_session(session_id, keep_recent_count=keep_recent_count)
        except Exception as exc:
            logger.warning("Could not commit session %s: %s", session_id, exc)

    def get_session_context(self, session_id: str, token_budget: int = 2000) -> str:
        """The memory the server extracted for this session."""
        try:
            context = self._client.get_session_context(
                session_id, token_budget=token_budget
            )
        except Exception as exc:
            logger.warning("No session context for %s: %s", session_id, exc)
            return ""
        if isinstance(context, dict):
            return str(context.get("context", ""))
        return str(context)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def opposite_belief(self, belief: str) -> str:
        """The belief we argue toward when the user has not said."""
        return BELIEF_OPPOSITES.get(belief, "spherical-earth")

    def stats(self) -> dict[str, Any]:
        """Counts per worldview and category."""
        stats: dict[str, Any] = {"targets": {}, "total_wisdoms": 0}

        for tier in ("knowledge", "enrichment"):
            for target in self.list_targets(tier):
                per_target = {}
                for category in self.list_categories(target, tier):
                    count = len(self.list_wisdoms(target, category, tier))
                    per_target[category] = count
                    stats["total_wisdoms"] += count
                stats["targets"].setdefault(target, {}).update(per_target)

        return stats

    def health(self) -> dict[str, Any]:
        """Server health."""
        return self._client.health()

    def close(self) -> None:
        """Close the connection."""
        self._client.close()

    def __enter__(self) -> VikingClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
