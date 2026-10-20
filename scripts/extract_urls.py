#!/usr/bin/env python3
"""
Extract content from URLs using docling and save as markdown.

Features:
- Rate limiting with random delays to avoid IP blocking
- Realistic browser user agent
- YAML frontmatter with metadata
- No embedded images in output
- Batch extraction from priority levels
"""

import argparse
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from docling.document_converter import DocumentConverter

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

MIN_DELAY = 2.0
MAX_DELAY = 5.0

HIGH_PRIORITY_SOURCES = [
    {
        "name": "zetetic-astronomy",
        "url": "https://www.gutenberg.org/ebooks/69892",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "name": "one-hundred-proofs",
        "url": "https://www.loc.gov/item/52055019/",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "name": "biblical-cosmology",
        "url": "https://en.wikipedia.org/wiki/Biblical_cosmology",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "firmament",
        "url": "https://en.wikipedia.org/wiki/Firmament",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "near-eastern-cosmology",
        "url": "https://en.wikipedia.org/wiki/Ancient_Near_Eastern_cosmology",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "scripture-verses-firmament",
        "url": "https://www.openbible.info/topics/firmament",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "bhu-mandala",
        "url": "http://www.iskcon-truth.com/bhu-mandala/bhumandala-dvipas.html",
        "target": "flat-earth",
        "category": "vedic",
    },
    {
        "name": "vedic-flat-earth",
        "url": "https://www.iskcon-truth.com/bhu-mandala/earth-is-not-a-globe3.html",
        "target": "flat-earth",
        "category": "vedic",
    },
    {
        "name": "empirical-evidence",
        "url": "https://en.wikipedia.org/wiki/Empirical_evidence_for_the_spherical_shape_of_Earth",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "nasa-flat-earth",
        "url": "https://www.nasa.gov/audience/forstudents/5-8/features/nasa-knows/what-is-earth-58.html",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "britannica-spherical-earth",
        "url": "https://www.britannica.com/science/Spherical-Earth",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "discworld-geography",
        "url": "https://discworld.fandom.com/wiki/Discworld_geography",
        "target": "fictional",
        "category": "discworld",
    },
    {
        "name": "discworld-locations",
        "url": "https://wiki.lspace.org/List_of_Discworld_locations",
        "target": "fictional",
        "category": "discworld",
    },
    {
        "name": "norse-cosmology",
        "url": "https://en.wikipedia.org/wiki/Norse_cosmology",
        "target": "fictional",
        "category": "norse",
    },
    {
        "name": "nine-worlds",
        "url": "https://thewickedgriffin.com/9-worlds-of-norse-mythology/",
        "target": "fictional",
        "category": "norse",
    },
]

MEDIUM_PRIORITY_SOURCES = [
    {
        "name": "rowbotham-biography",
        "url": "https://en.wikipedia.org/wiki/Samuel_Rowbotham",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "name": "universal-zetetic-society",
        "url": "https://wiki.tfes.org/Universal_Zetetic_Society",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "name": "chapter-04-history",
        "url": "https://www.cantab.net/users/michael.behrend/ebooks/PlaneTruth/pages/Chapter_04.html",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "name": "flat-earth-society-faq",
        "url": "https://wiki.tfes.org/Frequently_Asked_Questions",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "name": "earth-has-dome",
        "url": "https://www.openbible.info/topics/earth_has_a_dome_over_it",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "flat-earth-bible",
        "url": "https://www.islamawareness.net/Christianity/flatearth.html",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "bible-verses-flat-earth",
        "url": "https://www.biblestudytools.com/topical-verses/bible-verses-about-flat-earth/",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "earth-dimension",
        "url": "https://www.iskcon-truth.com/bhu-mandala/earth-dimension.html",
        "target": "flat-earth",
        "category": "vedic",
    },
    {
        "name": "hinduism-flat-earth",
        "url": "https://www.harekrsna.com/sun/editorials/07-20/editorials18012.htm",
        "target": "flat-earth",
        "category": "vedic",
    },
    {
        "name": "india-earth-globe",
        "url": "https://www.harekrsna.com/sun/editorials/07-21/editorials18963.htm",
        "target": "flat-earth",
        "category": "vedic",
    },
    {
        "name": "understanding-bhu-mandala",
        "url": "https://www.ccdas.net/p/understanding-bhu-mandala",
        "target": "flat-earth",
        "category": "vedic",
    },
    {
        "name": "geodesy",
        "url": "https://en.wikipedia.org/wiki/Geodesy",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "satellite-geodesy",
        "url": "https://en.wikipedia.org/wiki/Satellite_geodesy",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "why-not-scientific",
        "url": "https://futurafeed.com/why-flat-earth-is-not-scientific/",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "geometry-evidence",
        "url": "https://profmattstrassler.com/2022/01/21/geometry-from-within-evidence-for-a-round-earth/",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "discworld-wiki",
        "url": "https://en.wikipedia.org/wiki/Discworld",
        "target": "fictional",
        "category": "discworld",
    },
    {
        "name": "discworld-mapp",
        "url": "https://en.wikipedia.org/wiki/The_Discworld_Mapp",
        "target": "fictional",
        "category": "discworld",
    },
    {
        "name": "compleat-atlas",
        "url": "https://wiki.lspace.org/Book:The_Compleat_Discworld_Atlas",
        "target": "fictional",
        "category": "discworld",
    },
    {
        "name": "norse-mythology-substack",
        "url": "https://norsemythology.substack.com/p/norse-cosmology-part-ii-the-shape",
        "target": "fictional",
        "category": "norse",
    },
    {
        "name": "old-norse-cosmology-intro",
        "url": "https://germanicmythology.com/original/cosmologyIntro.html",
        "target": "fictional",
        "category": "norse",
    },
    {
        "name": "old-norse-cosmology-detailed",
        "url": "http://www.germanicmythology.com/original/cosmology4.html",
        "target": "fictional",
        "category": "norse",
    },
    {
        "name": "norse-collector",
        "url": "https://www.thecollector.com/norse-mythology-cosmology/",
        "target": "fictional",
        "category": "norse",
    },
    {
        "name": "northern-shaman",
        "url": "https://www.northern-shaman.eu/cosmology",
        "target": "fictional",
        "category": "norse",
    },
]

LOW_PRIORITY_SOURCES = [
    {
        "name": "flat-earth-insanity-claims",
        "url": "https://flatearthinsanity.blogspot.com/2016/11/catalog-of-flat-earth-claims-refutations.html",
        "target": "flat-earth",
        "category": "victorian",
    },
    {
        "name": "does-bible-teach-flat",
        "url": "https://answersingenesis.org/astronomy/earth/does-bible-teach-earth-flat/",
        "target": "flat-earth",
        "category": "biblical",
    },
    {
        "name": "why-bhu-mandala-not-flat",
        "url": "https://www.ccdas.net/p/why-the-description-of-bhu-mandala-does-not-mean-the-earth-is-flat",
        "target": "flat-earth",
        "category": "vedic",
    },
    {
        "name": "how-know-earth-round",
        "url": "https://iqscience.com/how-do-we-know-that-earth-is-round/",
        "target": "spherical-earth",
        "category": "scientific",
    },
    {
        "name": "how-big-discworld",
        "url": "https://aleph-zero-heroes.info/posts/pratchett_discworld/",
        "target": "fictional",
        "category": "discworld",
    },
    {
        "name": "terry-pratchett-books",
        "url": "https://www.terrypratchettbooks.com/exploring-discworld/",
        "target": "fictional",
        "category": "discworld",
    },
    {
        "name": "norse-mythology-wikispeedia",
        "url": "https://dlab.epfl.ch/wikispeedia/wpcd/wp/n/Norse_mythology.htm",
        "target": "fictional",
        "category": "norse",
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


def create_frontmatter(
    source_url: str,
    target: str,
    category: str,
    extracted_date: str | None = None,
) -> str:
    """Create YAML frontmatter for the markdown file."""
    if extracted_date is None:
        extracted_date = datetime.now().strftime("%Y-%m-%d")
    
    return f"""---
source_url: {source_url}
extracted_date: {extracted_date}
extraction_tool: docling
target: {target}
category: {category}
---

"""


def extract_url(
    url: str,
    output_path: Path,
    target: str,
    category: str,
    converter: DocumentConverter | None = None,
) -> bool:
    """
    Extract content from a URL and save as markdown.
    
    Args:
        url: URL to extract
        output_path: Path to save the markdown file
        target: Target persuasion type (flat-earth, spherical-earth, etc.)
        category: Content category (victorian, biblical, etc.)
        converter: Optional pre-created DocumentConverter instance
        
    Returns:
        True if extraction succeeded, False otherwise
    """
    logger.info(f"Extracting: {url}")
    
    if converter is None:
        converter = DocumentConverter()
    
    try:
        result = converter.convert(url)
        markdown_content = result.document.export_to_markdown()
        
        if len(markdown_content) < 100:
            logger.warning(f"Content too short ({len(markdown_content)} chars): {url}")
            return False
        
        frontmatter = create_frontmatter(url, target, category)
        full_content = frontmatter + markdown_content
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_content, encoding="utf-8")
        
        logger.info(f"Saved: {output_path} ({len(markdown_content)} chars)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to extract {url}: {e}")
        return False


def extract_single(
    url: str,
    target: str,
    category: str,
    name: str,
    output_dir: Path,
) -> bool:
    """Extract a single URL with rate limiting."""
    output_path = output_dir / target / category / f"{name}.md"
    
    random_delay()
    converter = DocumentConverter()
    return extract_url(url, output_path, target, category, converter)


def extract_batch(
    sources: list[dict],
    output_dir: Path,
) -> tuple[int, int]:
    """
    Extract multiple URLs with rate limiting.
    
    Args:
        sources: List of source dictionaries with name, url, target, category
        output_dir: Base output directory
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    converter = DocumentConverter()
    success = 0
    failure = 0
    
    for i, source in enumerate(sources, 1):
        logger.info(f"\n[{i}/{len(sources)}] Processing: {source['name']}")
        
        output_path = (
            output_dir
            / source["target"]
            / source["category"]
            / f"{source['name']}.md"
        )
        
        if i > 1:
            random_delay()
        
        if extract_url(
            source["url"],
            output_path,
            source["target"],
            source["category"],
            converter,
        ):
            success += 1
        else:
            failure += 1
    
    return success, failure


def main():
    parser = argparse.ArgumentParser(
        description="Extract content from URLs using docling"
    )
    parser.add_argument(
        "--url",
        help="Single URL to extract",
    )
    parser.add_argument(
        "--target",
        choices=["flat-earth", "spherical-earth", "discworld", "norse"],
        help="Target persuasion type",
    )
    parser.add_argument(
        "--category",
        choices=["victorian", "biblical", "vedic", "scientific", "fictional"],
        help="Content category",
    )
    parser.add_argument(
        "--name",
        help="Output filename (without .md extension)",
    )
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low", "all"],
        default="high",
        help="Priority level for batch extraction",
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
        print("HIGH Priority Sources:")
        print("-" * 60)
        for s in HIGH_PRIORITY_SOURCES:
            print(f"  {s['name']:30} [{s['target']}/{s['category']}]")
        print(f"\nMEDIUM Priority Sources ({len(MEDIUM_PRIORITY_SOURCES)}):")
        print("-" * 60)
        for s in MEDIUM_PRIORITY_SOURCES:
            print(f"  {s['name']:30} [{s['target']}/{s['category']}]")
        print(f"\nLOW Priority Sources ({len(LOW_PRIORITY_SOURCES)}):")
        print("-" * 60)
        for s in LOW_PRIORITY_SOURCES:
            print(f"  {s['name']:30} [{s['target']}/{s['category']}]")
        return 0
    
    if args.url:
        if not all([args.target, args.category, args.name]):
            parser.error(
                "--url requires --target, --category, and --name"
            )
        
        success = extract_single(
            args.url,
            args.target,
            args.category,
            args.name,
            args.output_dir,
        )
        return 0 if success else 1
    
    if args.priority == "high":
        sources = HIGH_PRIORITY_SOURCES
    elif args.priority == "medium":
        sources = MEDIUM_PRIORITY_SOURCES
    elif args.priority == "low":
        sources = LOW_PRIORITY_SOURCES
    else:
        sources = HIGH_PRIORITY_SOURCES + MEDIUM_PRIORITY_SOURCES + LOW_PRIORITY_SOURCES
    
    logger.info(f"Starting batch extraction of {len(sources)} sources...")
    
    success, failure = extract_batch(sources, args.output_dir)
    
    logger.info(f"\nExtraction complete: {success} succeeded, {failure} failed")
    
    return 0 if failure == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
