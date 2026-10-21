#!/usr/bin/env python3
"""
Download the reference images for the knowledge base.

The images are the ones the lab argues about: the flat earth maps, the real
Earth from orbit, Yggdrasil, the Discworld. They live on Wikimedia Commons,
and the URLs are resolved through the Commons API, so a file that moves does
not break the list.

The list is deliberately short. An image tier is only worth having if it is
real, and a tier of two files is worse than no tier at all.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 800

# the commons api wants a descriptive agent, a browser one gets the robot
# policy thrown at it
USER_AGENTS = [
    "parallax-observer/1.0 (https://truth.parallax.observer; educational research) httpx",
    "parallax-observer/1.0 (educational research project; contact via the site)",
]

MIN_DELAY = 1.0
MAX_DELAY = 2.5

# name, commons file title, worldview, what it shows
IMAGE_SOURCES = [
    # --- flat earth ----------------------------------------------------
    (
        "flat-earth-map",
        "File:Flat Earth.png",
        "flat-earth",
        "The classic flat earth map, the one that started the argument in 1895.",
    ),
    (
        "ferguson-1893",
        "File:Orlando-Ferguson-flat-earth-map edit.jpg",
        "flat-earth",
        "Orlando Ferguson's flat earth map, the one the Flat Earth Society still prints.",
    ),
    (
        "azimuthal-projection",
        "File:Flat Earth Map Azhimutal Projection.png",
        "flat-earth",
        "The azimuthal projection flat earth maps use, with the north pole in the middle.",
    ),
    (
        "ferguson-portrait",
        "File:Orlando Ferguson image in flat earth map.jpg",
        "flat-earth",
        "Orlando Ferguson himself, the man who drew the map.",
    ),
    # --- spherical earth ------------------------------------------------
    (
        "blue-marble",
        "File:The Blue Marble, AS17-148-22727.jpg",
        "spherical-earth",
        "The Blue Marble, the whole Earth in one photograph from Apollo 17.",
    ),
    (
        "earth-from-apollo",
        "File:The Earth seen from Apollo 17.jpg",
        "spherical-earth",
        "The Earth from orbit, the curve that a flat model cannot produce.",
    ),
    # --- discworld ------------------------------------------------------
    (
        "discworld-emporium",
        "File:Discworld Emporium Wincanton.jpg",
        "discworld",
        "The emporium in Ankh-Morpork, a city on a disc.",
    ),
    (
        "rincephand-twoflower",
        "File:Rincewind and Twoflower.jpg",
        "discworld",
        "Rincewind and Twoflower, the wizard and the tourist.",
    ),
    # --- norse ----------------------------------------------------------
    (
        "yggdrasil",
        "File:Yggdrasil.jpg",
        "norse",
        "Yggdrasil, the world tree, with the nine worlds hung on its branches.",
    ),
    (
        "ash-yggdrasil",
        "File:The Ash Yggdrasil by Friedrich Wilhelm Heine.jpg",
        "norse",
        "The world tree as a drawing, with the worlds around the trunk.",
    ),
    (
        "bagge-yggdrasil",
        "File:Oluf Olufsen Bagge - Yggdrasil, The Mundane Tree 1847 - full page.jpg",
        "norse",
        "The mundane tree, drawn in 1847, nine worlds and all.",
    ),
]


def resolve_url(client: httpx.Client, title: str, width: int = THUMB_WIDTH) -> str | None:
    """The thumbnail url of a Commons file."""
    try:
        response = client.get(
            COMMONS_API,
            params={
                "action": "query",
                "titles": title,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": width,
                "format": "json",
                "formatversion": "2",
            },
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.error("could not resolve %s: %s", title, exc)
        return None

    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        logger.warning("%s does not exist on commons", title)
        return None

    info = pages[0].get("imageinfo")
    if not info:
        logger.warning("%s has no image info", title)
        return None

    return info[0].get("thumburl") or info[0].get("url")


def download_image(
    url: str,
    output_path: Path,
    client: httpx.Client,
    min_bytes: int = 5000,
) -> bool:
    """Download one image."""
    try:
        response = client.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()

        payload = response.content
        if len(payload) < min_bytes:
            logger.warning("%s is only %d bytes, skipping", url, len(payload))
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(payload)
        logger.info("saved %s (%d bytes)", output_path, len(payload))
        return True

    except Exception as exc:
        logger.error("failed %s: %s", url, exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the reference images")
    parser.add_argument("--output-dir", type=Path, default=Path("dataset"))
    parser.add_argument("--list-sources", action="store_true")
    parser.add_argument("--force", action="store_true", help="download again if it exists")
    args = parser.parse_args()

    if args.list_sources:
        print("Image sources:")
        print("-" * 78)
        for name, title, worldview, caption in IMAGE_SOURCES:
            print(f"  {name:<22} [{worldview:<16}] {caption}")
            print(f"  {'':<22} {'':<16} {title}")
        return 0

    headers = {"User-Agent": random.choice(USER_AGENTS)}
    success = 0
    failed = 0

    with httpx.Client(headers=headers) as client:
        for index, (name, title, worldview, _caption) in enumerate(IMAGE_SOURCES, 1):
            output_path = args.output_dir / "images" / worldview / f"{name}.jpg"

            if output_path.exists() and not args.force:
                logger.info("[%d/%d] %s already there", index, len(IMAGE_SOURCES), name)
                success += 1
                continue

            if index > 1:
                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

            url = resolve_url(client, title)
            if not url:
                failed += 1
                continue

            if download_image(url, output_path, client):
                success += 1
            else:
                failed += 1

    logger.info("done: %d succeeded, %d failed", success, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
