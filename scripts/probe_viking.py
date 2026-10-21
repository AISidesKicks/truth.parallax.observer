#!/usr/bin/env python3
"""
Probe the OpenViking server: is it up, and does it find the corpus?

Usage:
    python scripts/probe_viking.py
    python scripts/probe_viking.py --query "water finds its level"
    python scripts/probe_viking.py --tier knowledge
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from openviking_sdk import SyncHTTPClient

DEFAULT_SERVER = os.environ.get("OPENVIKING_URL", "http://localhost:1933")
API_KEY = os.environ.get("OPENVIKING_API_KEY", "")
ACCOUNT = os.environ.get("OPENVIKING_ACCOUNT", "")

DEFAULT_QUERIES = {
    "flat-earth": "why the earth is flat, water finds its level",
    "spherical-earth": "how gravity and density explain weight",
    "discworld": "the world is a disc carried by elephants on a turtle",
    "norse": "the nine worlds hang from the branches of Yggdrasil",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe the OpenViking server")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--user", default="default")
    parser.add_argument("--api-key", default=API_KEY)
    parser.add_argument("--account", default=ACCOUNT)
    parser.add_argument("--tier", default="knowledge", help="knowledge or enrichment")
    parser.add_argument("--query", help="one query instead of the built in set")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    client = SyncHTTPClient(
        url=args.server,
        api_key=args.api_key,
        user=args.user,
        account=args.account,
    )
    client.initialize()

    print(f"server: {args.server}")
    print(f"health: {client.health()}")

    try:
        status = client.get_status(format="json")
        print("\n--- status ---")
        print(json.dumps(status, ensure_ascii=False, indent=2)[:1200])
    except Exception as exc:
        print(f"\nstatus unavailable: {exc}")

    print("\n--- tree ---")
    try:
        tree = client.tree(f"viking://~/resources/{args.tier}", level_limit=2, node_limit=40)
        print(json.dumps(tree, ensure_ascii=False, indent=2)[:2000])
    except Exception as exc:
        print(f"tree unavailable: {exc}")

    print("\n--- scoped retrieval ---")
    queries = {"custom": args.query} if args.query else DEFAULT_QUERIES

    for worldview, query in queries.items():
        try:
            found = client.find(
                query=query,
                target_uri=f"viking://~/resources/{args.tier}/{worldview}/",
                limit=args.limit,
                options={"include_provenance": True},
            )
        except Exception as exc:
            print(f"\n{worldview}: failed, {exc}")
            continue

        hits = found.get("resources", [])
        print(f"\n{worldview}: {len(hits)} hits")
        for hit in hits:
            score = hit.get("score")
            score = f"{score:.3f}" if isinstance(score, float) else score
            print(f"  L{hit.get('level')} {score} {hit.get('uri')}")
            abstract = hit.get("abstract")
            if abstract:
                print(f"      {str(abstract)[:140]}")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
