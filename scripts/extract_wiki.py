#!/usr/bin/env python3
"""
Pull wiki pages through the MediaWiki API.

docling fetches pages like a browser, which the Fandom wikis refuse. The
MediaWiki API is open, gives clean rendered HTML and lets us list whole
categories in one go, which is how the thin worldviews get their depth.

Usage:
    python scripts/extract_wiki.py --list
    python scripts/extract_wiki.py --group discworld
    python scripts/extract_wiki.py --group discworld --group norse
    python scripts/extract_wiki.py --group all --dry-run
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import httpx
from markdownify import markdownify as to_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

USER_AGENT = "parallax-observer/1.0 (educational research; https://truth.parallax.observer)"

# the wikis rate limit hard, so be slow and back off
REQUEST_DELAY = 2.5
MAX_RETRIES = 4

LSPACE = "https://wiki.lspace.org/api.php"
FANDOM_DISCWORLD = "https://discworld.fandom.com/api.php"
WIKIPEDIA = "https://en.wikipedia.org/w/api.php"
WIKISOURCE = "https://en.wikisource.org/w/api.php"

OUTPUT_DIR = Path("dataset")

# wiki html that is navigation, not content
SKIP_CLASSES = {
    "navbox",
    "navbox-inner",
    "navbox-content",
    "vertical-navbox",
    "metadata",
    "reflist",
    "references",
    "mw-editsection",
    "mw-jump-link",
    "thumb",
    "thumbinner",
    "thumbcaption",
    "hatnote",
    "infobox",
    "infobox-above",
    "infobox-below",
    "sidebar",
    "ambox",
    "ambox-text",
    "noprint",
    "mw-empty-elt",
    "portal",
    "portal-content",
    "catlinks",
    "printfooter",
    "mw-indicators",
    "mw-references-wrap",
    "sistersitebox",
    "shortdescription",
    "plainlist",
    "gallery",
    "toc",
    "toctitle",
    "mw-table-nowrap",
}

SKIP_IDS = {
    "toc",
    "catlinks",
    "filetoc",
    "siteSub",
    "contentSub",
    "mw-navigation",
    "footer",
    "header",
}


@dataclass
class WikiSource:
    """One batch of pages to pull from one wiki."""

    name: str
    wiki: str
    target: str
    category: str
    prefix: str
    pages: list[str] = field(default_factory=list)
    from_category: str = ""
    limit: int = 60
    skip_existing: bool = True


# --------------------------------------------------------------------------
# The source list
# --------------------------------------------------------------------------

WIKI_SOURCES: list[WikiSource] = [
    # --- Discworld --------------------------------------------------------
    WikiSource(
        name="lspace-discworld-geography",
        wiki=LSPACE,
        target="fictional",
        category="discworld",
        prefix="lspace-geography",
        from_category="Category:Discworld geography",
        limit=80,
    ),
    WikiSource(
        name="lspace-discworld-culture",
        wiki=LSPACE,
        target="fictional",
        category="discworld",
        prefix="lspace-culture",
        from_category="Category:Discworld culture",
        limit=80,
    ),
    WikiSource(
        name="lspace-discworld-concepts",
        wiki=LSPACE,
        target="fictional",
        category="discworld",
        prefix="lspace-concept",
        from_category="Category:Discworld concepts",
        limit=60,
    ),
    WikiSource(
        name="lspace-discworld-characters",
        wiki=LSPACE,
        target="fictional",
        category="discworld",
        prefix="lspace-character",
        from_category="Category:Discworld characters",
        limit=60,
    ),
    WikiSource(
        name="fandom-ankh-morpork-locations",
        wiki=FANDOM_DISCWORLD,
        target="fictional",
        category="discworld",
        prefix="fandom-location",
        from_category="Category:Ankh-Morpork locations",
        limit=60,
    ),
    WikiSource(
        name="fandom-cities",
        wiki=FANDOM_DISCWORLD,
        target="fictional",
        category="discworld",
        prefix="fandom-city",
        from_category="Category:Cities",
        limit=40,
    ),
    # --- Norse ------------------------------------------------------------
    WikiSource(
        name="wiki-poetic-edda",
        wiki=WIKISOURCE,
        target="fictional",
        category="norse",
        prefix="edda-poetic",
        pages=[
            "The Poetic Edda (tr. Bellows)/Voluspo",
            "The Poetic Edda (tr. Bellows)/Grimnismol",
            "The Poetic Edda (tr. Bellows)/Hovamol",
            "The Poetic Edda (tr. Bellows)/Lokasenna",
            "The Poetic Edda (tr. Bellows)/Vafthruthnismol",
            "The Poetic Edda (tr. Bellows)/Baldrs Draumar",
            "The Poetic Edda (tr. Bellows)/Thrymskvitha",
            "The Poetic Edda (tr. Bellows)/Hyndluljoth",
            "The Poetic Edda (tr. Bellows)/Helgakvitha Hundingsbana I",
            "The Poetic Edda (tr. Bellows)/Helgakvitha Hjordvarthssonar",
            "The Poetic Edda (tr. Bellows)/Sigrdrifumol",
            "The Poetic Edda (tr. Bellows)/Skirnismol",
            "The Poetic Edda (tr. Bellows)/Sigurtharkvitha en Skamma",
            "The Poetic Edda (tr. Bellows)/Fafnismol",
            "The Poetic Edda (tr. Bellows)/Reginsmol",
            "The Poetic Edda (tr. Bellows)/Atlakvitha en Grönlenzska",
            "The Poetic Edda (tr. Bellows)/Atlamol en Grönlenzku",
            "The Poetic Edda (tr. Bellows)/Harbarthsljoth",
            "The Poetic Edda (tr. Bellows)/Hymiskvitha",
            "The Poetic Edda (tr. Bellows)/Helreith Brynhildar",
            "The Poetic Edda (tr. Bellows)/Svipdagsmol",
            "The Poetic Edda (tr. Bellows)/Alvissmol",
            "The Poetic Edda (tr. Bellows)/Guthrunarkvitha I",
            "The Poetic Edda (tr. Bellows)/Guthrunarkvitha II, en Forna",
            "The Poetic Edda (tr. Bellows)/Guthrunarkvitha III",
            "The Poetic Edda (tr. Bellows)/Guthrunarhvot",
            "The Poetic Edda (tr. Bellows)/Brot af Sigurtharkvithu",
            "The Poetic Edda (tr. Bellows)/Drap Niflunga",
            "The Poetic Edda (tr. Bellows)/Hamthesmol",
            "The Poetic Edda (tr. Bellows)/Oddrunargratr",
            "The Poetic Edda (tr. Bellows)/Völundarkvitha",
            "The Poetic Edda (tr. Bellows)/Gripisspo",
        ],
    ),
    WikiSource(
        name="wiki-norse-cosmology-pages",
        wiki=WIKIPEDIA,
        target="fictional",
        category="norse",
        prefix="wiki",
        pages=[
            "Yggdrasil",
            "Nine Realms",
            "Ragnarök",
            "Bifröst",
            "Asgard",
            "Midgard",
            "Valhalla",
            "Jötunheim",
            "Hel (folklore)",
            "World tree",
            "Poetic Edda",
            "Prose Edda",
            "Ymir",
            "Surtr",
            "Ask and Embla",
            "Germanic paganism",
            "Valkyrie",
            "Fylgja",
            "Odin",
            "Loki",
            "Þórr",
            "Freyja",
            "Sif",
            "Skaði",
            "Njord",
            "Týr",
            "Ullr",
            "Heimdall",
            "Mímir",
            "Ratatoskr",
            "Hugin and Munin",
            "Garmr",
            "Fenrir",
            "Jörmungandr",
            "Sleipnir",
            "Náglfar",
            "Vanaheim",
            "Helheim",
            "Gimlé",
            "Fólkvangr",
            "Völuspá",
            "Grímnismál",
            "Hávamál",
            "Loka-senna",
            "Fimbulwinter",
            "Ragnarok in popular culture",
            "Norse mythology in popular culture",
        ],
    ),
]


# --------------------------------------------------------------------------
# HTML cleaning
# --------------------------------------------------------------------------


class WikiHTMLCleaner(HTMLParser):
    """Strip the navigation, the infoboxes and the reference lists."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.skip_tags: list[str] = []
        self.seen_content = False

    def _should_skip(self, tag: str, attrs: dict[str, str]) -> bool:
        if tag in {"script", "style", "noscript"}:
            return True

        classes = set((attrs.get("class") or "").split())
        if classes & SKIP_CLASSES:
            return True

        element_id = attrs.get("id") or ""
        return element_id in SKIP_IDS

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}

        if self.skip_depth:
            if tag in {"div", "table", "ul", "ol", "p", "span"}:
                self.skip_depth += 1
            return

        if self._should_skip(tag, attrs):
            self.skip_depth = 1
            self.skip_tags.append(tag)
            return

        # a table before any prose is the infobox, drop it
        if tag == "table" and not self.seen_content:
            self.skip_depth = 1
            self.skip_tags.append(tag)
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self.parts.append(f"\n\n{'#' * level} ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "p":
            self.seen_content = True
            self.parts.append("\n\n")
        elif tag in {"div", "tr", "blockquote"} or tag == "table":
            self.parts.append("\n\n")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth:
            if tag == self.skip_tags[-1]:
                self.skip_depth = 0
                self.skip_tags.pop()
            elif tag in {"div", "table", "ul", "ol", "p", "span"}:
                self.skip_depth = max(1, self.skip_depth - 1)
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "table", "ul", "ol"}:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def html_to_markdown(html: str) -> str:
    """Rendered wiki HTML into clean markdown."""
    cleaner = WikiHTMLCleaner()
    cleaner.feed(html)
    body = cleaner.text()

    # the headings the cleaner produced are not html, markdownify would eat them
    body = re.sub(r"\n{3,}", "\n\n", body)
    markdown = to_markdown(body, heading_style="ATX")

    # markdownify turns the fake headings back into text, put them back
    markdown = re.sub(r"^(#{1,6})\s*", r"\1 ", markdown, flags=re.M)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    return markdown.strip()


# --------------------------------------------------------------------------
# The API
# --------------------------------------------------------------------------


def api_get(client: httpx.Client, wiki: str, params: dict) -> dict:
    """One API call, with a polite delay and a back off on rate limits."""
    params = {**params, "format": "json", "formatversion": "2"}
    delay = REQUEST_DELAY

    for attempt in range(MAX_RETRIES):
        response = client.get(wiki, params=params)

        if response.status_code == 429:
            wait = delay * (2**attempt)
            logger.warning("rate limited, waiting %.0fs", wait)
            time.sleep(wait)
            delay = REQUEST_DELAY
            continue

        response.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return response.json()

    raise RuntimeError(f"still rate limited after {MAX_RETRIES} tries")


def category_pages(client: httpx.Client, wiki: str, category: str, limit: int) -> list[str]:
    """The pages in a category."""
    titles: list[str] = []
    continuation = ""

    while len(titles) < limit:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": min(50, limit - len(titles)),
            "cmnamespace": 0,
        }
        if continuation:
            params["cmcontinue"] = continuation

        try:
            data = api_get(client, wiki, params)
        except Exception as exc:
            logger.error("category %s failed: %s", category, exc)
            break

        members = data.get("query", {}).get("categorymembers", [])
        titles.extend(m["title"] for m in members)

        continuation = data.get("continue", {}).get("cmcontinue", "")
        if not continuation:
            break

    return titles[:limit]


def page_html(client: httpx.Client, wiki: str, title: str) -> str:
    """The rendered HTML of one page."""
    data = api_get(
        client,
        wiki,
        {
            "action": "parse",
            "page": title,
            "prop": "text",
            "redirects": 1,
            "disableeditsection": 1,
        },
    )
    return data.get("parse", {}).get("text", "")


def slugify(text: str) -> str:
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"[^A-Za-z0-9\-_/]", "", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-").lower()


def page_url_base(wiki: str) -> str:
    """The human readable page url for an api endpoint."""
    base = re.sub(r"/w/api\.php$", "", wiki)
    base = re.sub(r"/api\.php$", "", base)
    return f"{base}/wiki/"


def frontmatter(source_url: str, target: str, category: str) -> str:
    return f"""---
source_url: {source_url}
extracted_date: {datetime.now().strftime("%Y-%m-%d")}
extraction_tool: mediawiki-api
target: {target}
category: {category}
---

"""


def extract_source(
    client: httpx.Client,
    source: WikiSource,
    output_dir: Path,
    dry_run: bool,
    force: bool = False,
) -> tuple[int, int]:
    """Pull one batch of pages."""
    if source.from_category:
        pages = category_pages(client, source.wiki, source.from_category, source.limit)
    else:
        pages = list(source.pages)

    logger.info("%s: %d pages", source.name, len(pages))

    target_dir = output_dir / source.target / source.category
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    base = page_url_base(source.wiki)
    ok = 0
    failed = 0

    for title in pages:
        slug = slugify(title.replace("/", "-"))
        output_path = target_dir / f"{source.prefix}-{slug}.md"

        if source.skip_existing and output_path.exists() and not force:
            logger.debug("skip %s", title)
            ok += 1
            continue

        try:
            html = page_html(client, source.wiki, title)
        except Exception as exc:
            logger.warning("failed %s: %s", title, exc)
            failed += 1
            continue

        markdown = html_to_markdown(html)
        if len(markdown) < 400:
            logger.debug("too short, skipping %s (%d chars)", title, len(markdown))
            failed += 1
            continue

        if dry_run:
            logger.info("  would write %s (%d chars)", output_path.name, len(markdown))
        else:
            url = f"{base}{title.replace(' ', '_')}"
            output_path.write_text(
                frontmatter(url, source.target, source.category) + markdown,
                encoding="utf-8",
            )
        ok += 1

    return ok, failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull wiki pages through the MediaWiki API")
    parser.add_argument("--group", action="append", help="source name prefix, repeatable")
    parser.add_argument("--list", action="store_true", help="list the sources and exit")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="re-fetch pages that exist")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    if args.list:
        for source in WIKI_SOURCES:
            count = source.limit if source.from_category else len(source.pages)
            print(f"{source.name:<38} {source.target}/{source.category:<10} {count:>4} pages")
        return 0

    selected = WIKI_SOURCES
    if args.group and "all" not in args.group:
        selected = [
            source
            for source in WIKI_SOURCES
            if any(source.name.startswith(group) for group in args.group)
        ]
        if not selected:
            print("no source matched", file=sys.stderr)
            return 1

    ok = 0
    failed = 0
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=60.0,
        follow_redirects=True,
    ) as client:
        for source in selected:
            source_ok, source_failed = extract_source(
                client, source, args.output_dir, args.dry_run, args.force
            )
            ok += source_ok
            failed += source_failed

    logger.info("done: %d pulled, %d skipped or failed", ok, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
