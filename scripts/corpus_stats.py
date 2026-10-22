#!/usr/bin/env python3
"""
How big is the corpus, and what does the memory server hold?

The readme and the site quote these numbers, so this script is the one
source for them.

Two sets of numbers:

    on disk       the wisdom folders under facts/knowledge and facts/enrichment
    in the index  the records the memory server holds

Usage:
    python scripts/corpus_stats.py
    python scripts/corpus_stats.py --server http://localhost:1933
    python scripts/corpus_stats.py --json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_SERVER = "http://localhost:1933"
TIERS = ("knowledge", "enrichment")

# the project root, so the script works from any folder
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FACTS = ROOT / "facts"

# the two naming conventions, the knowledge tier is already OpenViking style
CONTENT_NAMES = ("content.md", "l2.content.md")


def load_dotenv_if_there() -> None:
    """Read the .env of the project, if it is there."""
    load_dotenv(ROOT / ".env")


def count_on_disk(facts: Path) -> dict[str, dict[str, int]]:
    """The wisdoms per worldview and tier, counted on disk."""
    counts: dict[str, dict[str, int]] = {tier: {} for tier in TIERS}

    for tier in TIERS:
        root = facts / tier
        if not root.is_dir():
            continue

        for worldview in sorted(root.iterdir()):
            if not worldview.is_dir():
                continue

            entries = 0
            for candidate in worldview.rglob("*"):
                if not candidate.is_dir():
                    continue
                if any((candidate / name).exists() for name in CONTENT_NAMES):
                    entries += 1

            counts[tier][worldview.name] = entries

    return counts


def server_records(server: str) -> dict[str, int | str | None]:
    """What the memory server holds."""
    try:
        from openviking_sdk import SyncHTTPClient

        client = SyncHTTPClient(
            url=server,
            api_key=os.environ.get("OPENVIKING_API_KEY", ""),
            user=os.environ.get("OPENVIKING_USER", "default"),
            account=os.environ.get("OPENVIKING_ACCOUNT", ""),
            timeout=60.0,
        )
        client.initialize()
    except Exception as exc:
        return {"error": str(exc)}

    try:
        status = client.get_status(format="json")
        components = status.get("components", {})
        vikingdb = components.get("vikingdb", {}).get("status", {})
        queue = components.get("queue", {}).get("status", {}).get("summary", {})

        return {
            "vectors": vikingdb.get("vector_count"),
            "queued": queue.get("total"),
            "errors": queue.get("errors"),
            "healthy": components.get("vikingdb", {}).get("is_healthy"),
        }
    except Exception as exc:
        return {"error": str(exc)}
    finally:
        with contextlib.suppress(Exception):
            client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Corpus statistics")
    parser.add_argument("--facts", default=str(DEFAULT_FACTS))
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--json", action="store_true", help="machine readable output")
    args = parser.parse_args()

    load_dotenv_if_there()

    disk = count_on_disk(Path(args.facts))
    server = server_records(args.server)

    if args.json:
        print(
            json.dumps(
                {"disk": disk, "server": server},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print("the corpus on disk")
    print()
    header = f"{'worldview':<18}{'knowledge':>10}{'ammunition':>13}"
    print(header)
    print("-" * len(header))

    worldviews = sorted(set(disk["knowledge"]) | set(disk["enrichment"]))
    for worldview in worldviews:
        knowledge = disk["knowledge"].get(worldview, 0)
        enrichment = disk["enrichment"].get(worldview, 0)
        print(f"{worldview:<18}{knowledge:>10}{enrichment:>13}")

    total_knowledge = sum(disk["knowledge"].values())
    total_enrichment = sum(disk["enrichment"].values())
    print("-" * len(header))
    print(f"{'total':<18}{total_knowledge:>10}{total_enrichment:>13}")

    print()
    print("the memory server")
    print()
    if "error" in server:
        print(f"  not reachable: {server['error']}")
    else:
        print(f"  indexed records: {server.get('vectors')}")
        print(f"  queued records:  {server.get('queued')}")
        print(f"  failed records:  {server.get('errors')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
