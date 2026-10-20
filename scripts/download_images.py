#!/usr/bin/env python3
"""
Download reference images for the knowledge base.

Features:
- Rate limiting with random delays
- Realistic browser user agent
- Proper image file extension handling
"""

import argparse
import logging
import random
import sys
import time
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

MIN_DELAY = 3.0
MAX_DELAY = 8.0

IMAGE_SOURCES = [
    {
        "name": "flat-earth-map",
        "url": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Flat_earth.png",
        "category": "flat-earth",
        "extension": "png",
    },
    {
        "name": "ferguson-1893",
        "url": "https://upload.wikimedia.org/wikipedia/commons/9/96/Orlando_Ferguson_flat_earth_map_edit.jpg",
        "category": "flat-earth",
        "extension": "jpg",
    },
    {
        "name": "discworld-cover",
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/47/Terry_Pratchett_The_Colour_of_Magic.jpg",
        "category": "discworld",
        "extension": "jpg",
    },
    {
        "name": "world-tree",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Yggdrasill.png/600px-Yggdrasill.png",
        "category": "norse",
        "extension": "png",
    },
    {
        "name": "earth-from-space",
        "url": "https://upload.wikimedia.org/wikipedia/commons/c/cb/The_Blue_Marble_%28remastered%29.jpg",
        "category": "spherical-earth",
        "extension": "jpg",
    },
]


def random_delay() -> None:
    """Sleep for a random duration to avoid rate limiting."""
    delay = random.uniform(MIN_DELAY, MAX_DELAY)
    logger.debug(f"Waiting {delay:.2f}s before next request...")
    time.sleep(delay)


def get_random_user_agent() -> str:
    """Return a random browser user agent string."""
    return random.choice(USER_AGENTS)


def get_image_extension(url: str, content_type: str | None = None) -> str:
    """Determine image file extension from URL or content type."""
    if content_type:
        if "png" in content_type:
            return "png"
        if "jpeg" in content_type or "jpg" in content_type:
            return "jpg"
        if "gif" in content_type:
            return "gif"
        if "webp" in content_type:
            return "webp"
    
    url_lower = url.lower()
    if url_lower.endswith(".png"):
        return "png"
    if url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
        return "jpg"
    if url_lower.endswith(".gif"):
        return "gif"
    if url_lower.endswith(".webp"):
        return "webp"
    
    return "png"


def download_image(
    url: str,
    output_path: Path,
    session: requests.Session | None = None,
) -> bool:
    """
    Download an image from a URL.
    
    Args:
        url: Image URL
        output_path: Path to save the image
        session: Optional requests session
        
    Returns:
        True if download succeeded, False otherwise
    """
    logger.info(f"Downloading: {url}")
    
    if session is None:
        session = requests.Session()
    
    headers = {"User-Agent": get_random_user_agent()}
    
    try:
        response = session.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "")
        extension = get_image_extension(url, content_type)
        
        if output_path.suffix.lower() != f".{extension}":
            output_path = output_path.with_suffix(f".{extension}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Saved: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def download_batch(
    sources: list[dict],
    output_dir: Path,
) -> tuple[int, int]:
    """
    Download multiple images with rate limiting.
    
    Args:
        sources: List of source dictionaries
        output_dir: Base output directory
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    session = requests.Session()
    success = 0
    failure = 0
    
    for i, source in enumerate(sources, 1):
        logger.info(f"\n[{i}/{len(sources)}] Processing: {source['name']}")
        
        output_path = (
            output_dir
            / "images"
            / source["category"]
            / f"{source['name']}.{source['extension']}"
        )
        
        if i > 1:
            random_delay()
        
        if download_image(source["url"], output_path, session):
            success += 1
        else:
            failure += 1
    
    return success, failure


def main():
    parser = argparse.ArgumentParser(
        description="Download reference images for knowledge base"
    )
    parser.add_argument(
        "--url",
        help="Single image URL to download",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path",
    )
    parser.add_argument(
        "--category",
        help="Image category (for batch mode)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dataset"),
        help="Output directory (default: dataset/)",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List available sources and exit",
    )
    
    args = parser.parse_args()
    
    if args.list_sources:
        print("Image Sources:")
        print("-" * 60)
        for s in IMAGE_SOURCES:
            print(f"  {s['name']:25} [{s['category']}]")
        return 0
    
    if args.url:
        if not args.output:
            parser.error("--url requires --output")
        
        success = download_image(args.url, args.output)
        return 0 if success else 1
    
    logger.info(f"Starting batch download of {len(IMAGE_SOURCES)} images...")
    
    success, failure = download_batch(IMAGE_SOURCES, args.output_dir)
    
    logger.info(f"\nDownload complete: {success} succeeded, {failure} failed")
    
    return 0 if failure == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
