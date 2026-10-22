#!/usr/bin/env python3
"""
Is the stack actually working?

One command, seven checks, in order, and the first failure stops the run:

    1. the model server answers and serves the chat model and the encoder
    2. the encoder returns a vector of the right size for a probe string
    3. the memory server answers
    4. the corpus is on disk
    5. the index knows the corpus
    6. a scoped retrieval finds something
    7. a retrieval in a worldview that does not exist finds nothing

The last one is the important one. Without it, a retrieval that quietly
falls back to the whole corpus would look like a working stack.

Usage:
    python scripts/verify_stack.py
    python scripts/verify_stack.py --server http://localhost:1933
    python scripts/verify_stack.py --llm http://localhost:11433/v1
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

DEFAULT_LLM = "http://localhost:11433/v1"
DEFAULT_SERVER = "http://localhost:1933"

WORLDVIEWS = ("flat-earth", "spherical-earth", "discworld", "norse")
PROBE_QUERY = "how gravity and density explain weight"
GHOST_WORLDVIEW = "a-worldview-that-does-not-exist"

# the project root, so the script works from any folder
ROOT = Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / "config" / "models.toml"


class Failure(Exception):
    """A check did not pass."""


def load_dotenv_if_there() -> None:
    """Read the .env of the project, if it is there."""
    load_dotenv(ROOT / ".env")


def catalogue_models() -> tuple[list[str], list[str]]:
    """The chat models and the encoders, from the catalogue."""
    chat: list[str] = []
    embedding: list[str] = []

    if not CATALOGUE.exists():
        return chat, embedding

    try:
        import tomllib
    except ModuleNotFoundError:
        return chat, embedding

    try:
        with CATALOGUE.open("rb") as handle:
            data = tomllib.load(handle)
    except Exception:
        return chat, embedding

    for name, entry in data.items():
        if not isinstance(entry, dict):
            continue
        role = entry.get("role", "chat")
        if role == "embedding":
            embedding.append(name)
        else:
            chat.append(name)

    return chat, embedding


def settings_models() -> tuple[str, str]:
    """The chat model and the encoder, from the app settings."""
    try:
        sys.path.insert(0, str(ROOT))
        from src.config import get_settings

        settings = get_settings()
        return settings.llm_model, settings.embedding_model
    except Exception:
        return "granite-4.0-h-tiny", "embeddinggemma-2"


def expected_models() -> tuple[list[str], list[str]]:
    """Every model the app expects to be able to reach."""
    default_chat, default_embedding = settings_models()
    chat, embedding = catalogue_models()

    for name in [default_chat, *chat]:
        if name and name not in chat:
            chat.append(name)
    for name in [default_embedding, *embedding]:
        if name and name not in embedding:
            embedding.append(name)

    return chat, embedding


# ----------------------------------------------------------------------
# The checks
# ----------------------------------------------------------------------


def check_model_server(base_url: str, chat: list[str], embedding: list[str]) -> None:
    """The model server answers and serves what the app needs."""
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=15.0)
    except Exception as exc:
        raise Failure(f"the model server did not answer: {exc}") from exc

    if response.status_code != 200:
        raise Failure(f"the model server answered {response.status_code}")

    try:
        served = {entry.get("id") for entry in response.json().get("data", [])}
    except Exception as exc:
        raise Failure(f"the model server gave no list: {exc}") from exc

    missing = [name for name in [*chat, *embedding] if name not in served]
    if missing:
        raise Failure(f"the model server does not serve: {', '.join(missing)}")

    print(f"      serves {', '.join(sorted(served))}")


def check_embedding(base_url: str, model: str, dimension: int) -> None:
    """The encoder returns a vector of the right size."""
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/embeddings",
            json={"model": model, "input": "probe string"},
            timeout=60.0,
        )
    except Exception as exc:
        raise Failure(f"the encoder did not answer: {exc}") from exc

    if response.status_code != 200:
        raise Failure(f"the encoder answered {response.status_code}: {response.text[:200]}")

    try:
        vector = response.json()["data"][0]["embedding"]
    except Exception as exc:
        raise Failure(f"the encoder gave no vector: {exc}") from exc

    if len(vector) != dimension:
        raise Failure(f"the encoder returned {len(vector)} dimensions, expected {dimension}")

    print(f"      {model} returned {len(vector)} dimensions")


def check_memory_server(server: str) -> None:
    """The memory server answers."""
    try:
        response = httpx.get(f"{server.rstrip('/')}/health", timeout=15.0)
    except Exception as exc:
        raise Failure(f"the memory server did not answer: {exc}") from exc

    if response.status_code != 200:
        raise Failure(f"the memory server answered {response.status_code}")

    try:
        health = response.json()
    except Exception as exc:
        raise Failure(f"the memory server gave no health: {exc}") from exc

    if not health.get("healthy", True):
        raise Failure(f"the memory server says it is not healthy: {health}")

    print(f"      {health.get('version', 'unknown')} is up")


def check_corpus_on_disk(facts: Path) -> None:
    """The corpus is on disk."""
    knowledge = list(facts.glob("knowledge/*/*/*/content.md"))
    enrichment = list(facts.glob("enrichment/*/*/*/l2.content.md"))

    if not knowledge:
        raise Failure(f"no knowledge entries under {facts / 'knowledge'}")
    if not enrichment:
        raise Failure(f"no enrichment entries under {facts / 'enrichment'}")

    print(f"      {len(knowledge)} knowledge entries, {len(enrichment)} ammunition entries")


def make_client(server: str):
    """The memory client, with the key of the user."""
    from openviking_sdk import SyncHTTPClient

    client = SyncHTTPClient(
        url=server,
        api_key=os.environ.get("OPENVIKING_API_KEY", ""),
        user=os.environ.get("OPENVIKING_USER", "default"),
        account=os.environ.get("OPENVIKING_ACCOUNT", ""),
        timeout=120.0,
    )
    client.initialize()
    return client


def check_index(client) -> None:
    """The index knows the corpus."""
    entries = client.ls("viking://~/resources/knowledge")
    if isinstance(entries, dict):
        entries = entries.get("entries", []) or entries.get("items", [])

    names = {entry.get("name") for entry in entries if entry.get("isDir")}
    missing = [worldview for worldview in WORLDVIEWS if worldview not in names]

    if missing:
        raise Failure(f"the index does not know: {', '.join(missing)}")

    print(f"      the index knows {', '.join(sorted(names))}")


def check_scoped_retrieval(client) -> None:
    """A scoped retrieval finds something."""
    found = client.find(
        query=PROBE_QUERY,
        target_uri="viking://~/resources/knowledge/spherical-earth/",
        limit=3,
        options={"include_provenance": True},
    )

    hits = found.get("resources", [])
    if not hits:
        raise Failure("the scoped retrieval found nothing")

    best = hits[0]
    score = best.get("score")
    score = f"{score:.3f}" if isinstance(score, float) else score
    print(f"      {len(hits)} hits, the best one scores {score}")


def check_scoped_to_nothing(client) -> None:
    """A retrieval in a worldview that does not exist finds nothing."""
    found = client.find(
        query=PROBE_QUERY,
        target_uri=f"viking://~/resources/knowledge/{GHOST_WORLDVIEW}/",
        limit=3,
        options={"include_provenance": True},
    )

    hits = found.get("resources", [])
    if hits:
        raise Failure(
            f"the retrieval in a worldview that does not exist found {len(hits)} hits, "
            "so the scoping is not real"
        )

    print("      nothing came back, so the scoping is real")


# ----------------------------------------------------------------------


def main() -> int:
    load_dotenv_if_there()

    parser = argparse.ArgumentParser(description="Verify the stack")
    parser.add_argument("--llm", default=os.environ.get("LLM_API_BASE", DEFAULT_LLM))
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--facts", default=str(ROOT / "facts"))
    parser.add_argument("--dimension", type=int, default=768)
    args = parser.parse_args()

    chat, embedding = expected_models()

    checks = [
        ("the model server answers", lambda: check_model_server(args.llm, chat, embedding)),
        (
            "the encoder answers",
            lambda: check_embedding(args.llm, embedding[0], args.dimension),
        ),
        ("the memory server answers", lambda: check_memory_server(args.server)),
        ("the corpus is on disk", lambda: check_corpus_on_disk(Path(args.facts))),
    ]

    client = None
    try:
        for number, (title, run) in enumerate(checks, start=1):
            print(f"{number}. {title}")
            try:
                run()
            except Failure as exc:
                print(f"      FAILED: {exc}")
                print()
                print(f"the stack is not working, check {number} failed")
                return 1

        print("5. the index knows the corpus")
        try:
            client = make_client(args.server)
            check_index(client)
        except Failure as exc:
            print(f"      FAILED: {exc}")
            print()
            print("the stack is not working, check 5 failed")
            return 1

        print("6. a scoped retrieval finds something")
        try:
            check_scoped_retrieval(client)
        except Failure as exc:
            print(f"      FAILED: {exc}")
            print()
            print("the stack is not working, check 6 failed")
            return 1

        print("7. a retrieval in a worldview that does not exist finds nothing")
        try:
            check_scoped_to_nothing(client)
        except Failure as exc:
            print(f"      FAILED: {exc}")
            print()
            print("the stack is not working, check 7 failed")
            return 1

    finally:
        if client is not None:
            with contextlib.suppress(Exception):
                client.close()

    print()
    print("the stack is working")
    return 0


if __name__ == "__main__":
    sys.exit(main())
