#!/usr/bin/env python3
"""
Seed the OpenViking workspace from the wisdom corpus.

The corpus on disk uses two naming conventions:

    facts/enrichment/<worldview>/<category>/<wisdom>/
        l0.abstract, l1.overview, l2.content.md

    facts/knowledge/<worldview>/<category>/<wisdom>/
        content.md, .abstract.md, .overview.md

OpenViking wants the tier files under dot names:

    <workspace>/viking/<account>/resources/<tier>/<worldview>/<category>/<wisdom>/
        .abstract.md, .overview.md, content.md

So the enrichment tier gets renamed on the way in, the knowledge tier is
already right, and then the index is rebuilt with vectors_only. No model call,
the summaries we already wrote are kept as they are.

Usage:
    python scripts/migrate_to_viking.py --dry-run
    python scripts/migrate_to_viking.py --reindex
    python scripts/migrate_to_viking.py --tier enrichment --reindex
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

from openviking_sdk import SyncHTTPClient

FACTS_DIR = Path("facts")
DEFAULT_WORKSPACE = Path("memory/openviking")
DEFAULT_SERVER = os.environ.get("OPENVIKING_URL", "http://localhost:1933")
API_KEY = os.environ.get("OPENVIKING_API_KEY", "")
ACCOUNT = os.environ.get("OPENVIKING_ACCOUNT", "")

# tier name -> (source folder, is the naming already OpenViking style)
TIERS = {
    "enrichment": ("enrichment", False),
    "knowledge": ("knowledge", True),
}

# source file -> OpenViking tier file
ENRICHMENT_RENAME = {
    "l0.abstract": ".abstract.md",
    "l1.overview": ".overview.md",
    "l2.content.md": "content.md",
}

# the OpenViking metadata file name
METADATA_NAME = ".metadata.yaml"


def find_account(workspace: Path) -> str:
    """The account folder inside the workspace, usually 'default'."""
    viking_dir = workspace / "viking"
    if not viking_dir.is_dir():
        return "default"
    accounts = [d.name for d in viking_dir.iterdir() if d.is_dir()]
    if "default" in accounts:
        return "default"
    return accounts[0] if accounts else "default"


def copy_wisdom(source: Path, target: Path, already_named: bool) -> int:
    """Copy one wisdom into the workspace, renaming the tier files."""
    target.mkdir(parents=True, exist_ok=True)
    copied = 0

    for item in source.iterdir():
        if not item.is_file():
            continue

        if already_named:
            destination = target / item.name
        else:
            destination = target / ENRICHMENT_RENAME.get(item.name, item.name)

        shutil.copy2(item, destination)
        copied += 1

    return copied


def migrate(tier: str, workspace: Path, user: str, dry_run: bool) -> int:
    """Copy one tier of the corpus into the workspace."""
    source_folder, already_named = TIERS[tier]
    source_root = FACTS_DIR / source_folder
    if not source_root.exists():
        print(f"  no source folder: {source_root}")
        return 0

    account = find_account(workspace)
    # the corpus lives in the user namespace, because that is the only
    # namespace a user key is allowed to read and reindex
    target_root = (
        workspace / "viking" / account / "user" / user / "resources" / tier
    )

    if dry_run:
        print(f"  would write to {target_root}")
        count = sum(
            1
            for source in source_root.rglob("*")
            if source.is_dir() and (source / METADATA_NAME).exists()
        )
        print(f"  {count} wisdoms")
        return count

    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    wisdoms = 0
    files = 0
    for source in sorted(source_root.rglob("*")):
        if not source.is_dir():
            continue
        if not (source / METADATA_NAME).exists():
            continue
        target = target_root / source.relative_to(source_root)
        files += copy_wisdom(source, target, already_named)
        wisdoms += 1

    print(f"  {tier}: {wisdoms} wisdoms, {files} files -> {target_root}")
    return wisdoms


def reindex(
    server: str, workspace: Path, tier: str, user: str, api_key: str, account: str
) -> None:
    """Rebuild the vector index for one tier."""
    root = f"viking://resources/{tier}"

    client = SyncHTTPClient(
        url=server,
        api_key=api_key,
        user=user,
        account=account,
        timeout=1800.0,
    )
    client.initialize()

    print(f"  reindexing {root} (vectors only)")
    t0 = time.time()
    result = client.reindex(
        root,
        mode="vectors_only",
        wait=True,
        recursive=True,
        force=True,
    )
    summary = {
        key: result.get(key)
        for key in ("status", "scanned_records", "rebuilt_records", "failed_records")
        if key in result
    }
    print(f"  {json.dumps(summary)} in {time.time() - t0:.1f}s")
    client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the OpenViking workspace")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--user", default="default")
    parser.add_argument("--api-key", default=API_KEY)
    parser.add_argument("--account", default=ACCOUNT)
    parser.add_argument("--tier", choices=[*TIERS, "all"], default="all")
    parser.add_argument("--reindex", action="store_true", help="rebuild the vectors after")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    tiers = list(TIERS) if args.tier == "all" else [args.tier]

    print(f"workspace: {workspace}")
    print(f"server:    {args.server}")
    print(f"tiers:     {', '.join(tiers)}")
    print()

    total = 0
    for tier in tiers:
        total += migrate(tier, workspace, args.user, args.dry_run)

    if args.dry_run:
        print(f"\ndry run, {total} wisdoms would be written")
        return 0

    print()
    for tier in tiers:
        reindex(
            args.server, workspace, tier, args.user, args.api_key, args.account
        )

    print("\ndone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
