#!/usr/bin/env python3
"""
Prune the old session profiles.

The memory workspace keeps one folder per session:

    memory/openviking/user/<session_id>/profile/

The app writes the belief, the goal and the ledger of arguments there, and
nothing reads them back, because the app keeps its sessions in memory only.
Every test run leaves one behind, so the folder grows without bound.

This removes the oldest folders and keeps the newest ones.

Usage:
    python scripts/clean_sessions.py --keep 50
    python scripts/clean_sessions.py --keep 50 --dry-run
    python scripts/clean_sessions.py --dir memory/openviking/user --keep 10
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DIR = Path("memory/openviking/user")
DEFAULT_KEEP = 50


def session_time(folder: Path) -> float:
    """When the session was last touched.

    The newest file inside the folder wins, because the folder mtime only
    moves when an entry is added or removed.
    """
    newest = folder.stat().st_mtime
    for item in folder.rglob("*"):
        try:
            newest = max(newest, item.stat().st_mtime)
        except OSError:
            continue
    return newest


def collect(root: Path) -> list[tuple[float, Path]]:
    """Every session folder, oldest first."""
    if not root.is_dir():
        return []

    folders = [item for item in root.iterdir() if item.is_dir()]
    return sorted(((session_time(item), item) for item in folders), key=lambda pair: pair[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune the old session profiles")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="where the profiles live")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="how many to keep")
    parser.add_argument("--dry-run", action="store_true", help="only list what goes")
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        print(f"no such folder: {root}")
        return 0

    folders = collect(root)
    total = len(folders)
    keep = max(0, args.keep)
    doomed = folders[: max(0, total - keep)]

    print(f"profiles: {root}")
    print(f"  {total} folders, keeping the {min(keep, total)} newest")
    print()

    if not doomed:
        print("nothing to remove")
        return 0

    for stamp, folder in doomed:
        when = datetime.fromtimestamp(stamp).isoformat(timespec="seconds")
        print(f"  remove {folder.name}  ({when})")

    if args.dry_run:
        print(f"\ndry run, {len(doomed)} folders would go")
        return 0

    for _, folder in doomed:
        shutil.rmtree(folder, ignore_errors=True)

    print(f"\nremoved {len(doomed)} folders, {min(keep, total)} left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
