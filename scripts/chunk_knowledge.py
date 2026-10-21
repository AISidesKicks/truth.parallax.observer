#!/usr/bin/env python3
"""
Knowledge tier builder - turn the raw sources into source grounded wisdoms.

The enrichment tier (facts/enrichment) holds ammunition: single sentence
claims expanded by a model into L0, L1 and L2. This script builds the other
half, facts/knowledge, where the L2 content is the source text verbatim and
only the L0 essence and the L1 insight are generated.

That split matters. The fact checker needs something it can actually cite.

Usage:
    python scripts/chunk_knowledge.py                     # chunk only, no model
    python scripts/chunk_knowledge.py --summarize         # also generate L0 and L1
    python scripts/chunk_knowledge.py --summarize --target flat-earth
    python scripts/chunk_knowledge.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATASET_DIR = Path("dataset")
KNOWLEDGE_DIR = Path("facts/knowledge")

# source folder -> (target, category)
SOURCE_GROUPS = {
    "flat-earth/victorian": ("flat-earth", "victorian"),
    "flat-earth/biblical": ("flat-earth", "biblical"),
    "flat-earth/vedic": ("flat-earth", "vedic"),
    "spherical-earth/scientific": ("spherical-earth", "scientific"),
    "fictional/discworld": ("discworld", "fictional"),
    "fictional/norse": ("norse", "fictional"),
}

MIN_CHUNK_CHARS = 400
MAX_CHUNK_CHARS = 12000

# room for the thinking tokens of a reasoning model, on top of the answer
THINKING_BUDGET = 1500

# docling leaves navigation breadcrumbs in the text
JUNK_PATTERNS = [
    re.compile(r"^\[?(Share|Tweet|Facebook|Reddit|Print|Email|Bookmark)\]?\(javascript:void\(0\)\)$", re.I),
    re.compile(r"^\[?\d+\]?\(javascript:void\(0\)\)$"),
    re.compile(r"^\[\s*\[edit\]\([^)]*\)\s*\]$"),
    re.compile(r"^\[\[\s*\d+\s*\]\]\(#cite_note-.*\)$"),
    re.compile(r"^\[\[\s*\d+\s*\]\]\(#cite_ref-.*\)$"),
    re.compile(r"^<!--\s*image\s*-->$"),
    re.compile(r"^Back to Search Results$"),
    re.compile(r"^Jump to content$"),
    re.compile(r"^From Wikipedia, the free encyclopedia$"),
    re.compile(r"^\*\*Check out these other categories:\*\*$"),
    re.compile(r"^Main menu$"),
    re.compile(r"^Appearance$"),
    re.compile(r"^Personal tools$"),
    re.compile(r"^Namespaces$"),
    re.compile(r"^Views$"),
    re.compile(r"^Help$"),
    # the language switcher every Wikipedia article starts with
    re.compile(r"^\d+ languages$"),
    re.compile(r"^\d+ language$"),
    re.compile(r"^Add languages$"),
    re.compile(r"^\[Add links\]\([^)]*\)$"),
    re.compile(r"^- \[[A-Za-z /-]+\]\(https://[a-z-]+\.wikipedia\.org/[^)]*\)$"),
]

# footer widgets and navigation blocks that carry no knowledge
JUNK_HEADINGS = re.compile(
    r"^(recent posts|sign up to the newsletter|related posts|advertisement|"
    r"navigation|menu|cookie policy|privacy policy|subscribe|share this|"
    r"leave a comment|comments(\s*\d+)?|you may also like|popular posts|"
    r"categories|search|newsletter|sponsored|previous post|next post)$",
    re.I,
)

TOC_HEADING = re.compile(r"^#{1,6}\s*(table of contents|contents)\s*$", re.I)
FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    """One source grounded piece of knowledge."""

    heading: str
    heading_path: list[str]
    text: str
    slug: str
    source_file: str
    source_url: str
    target: str
    category: str
    word_count: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def uri(self) -> str:
        return f"viking://resources/knowledge/{self.target}/{self.category}/{self.slug}"


def strip_frontmatter(text: str) -> tuple[str, dict]:
    """Split YAML frontmatter from the body."""
    meta: dict = {}
    if not text.startswith("---"):
        return text, meta
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not match:
        return text, meta
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return text[match.end():], meta


def is_junk(line: str) -> bool:
    """True for the navigation breadcrumbs docling leaves behind."""
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.match(stripped) for pattern in JUNK_PATTERNS)


def clean_lines(lines: list[str]) -> list[str]:
    """Drop navigation junk and the table of contents block."""
    out: list[str] = []
    in_toc = False
    in_fence = False

    for line in lines:
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            out.append(line)
            continue

        if not in_fence:
            if TOC_HEADING.match(line):
                in_toc = True
                continue
            if in_toc:
                # the TOC runs until the next real heading
                if HEADING_RE.match(line):
                    in_toc = False
                else:
                    continue
            if is_junk(line):
                continue

        out.append(line)

    # collapse runs of blank lines
    cleaned: list[str] = []
    for line in out:
        if not line.strip() and cleaned and not cleaned[-1].strip():
            continue
        cleaned.append(line)

    return cleaned


def slugify(text: str, fallback: str) -> str:
    """URL safe slug, unique enough for a directory name."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return (text or fallback)[:60]


def split_headings(body: str) -> list[tuple[str, list[str], str]]:
    """Split a body into (heading, heading path, text) blocks.

    The split level is the deepest heading level the document really uses.
    Taking the absolute deepest level would split on footer widgets, which
    most sites mark up with a heading of their own.
    """
    lines = body.splitlines()

    levels: dict[int, list[tuple[int, str]]] = {}
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            levels.setdefault(level, []).append((index, match.group(2).strip()))

    if not levels:
        return [("", [], body)]

    split_level = pick_split_level(levels)
    blocks: list[tuple[str, list[str], str]] = []

    # the preamble before the first heading of the split level
    first = levels[split_level][0][0]
    preamble = "\n".join(lines[:first]).strip()
    if preamble:
        blocks.append(("", [], preamble))

    for position, (index, heading) in enumerate(levels[split_level]):
        if JUNK_HEADINGS.match(heading):
            continue

        start = index + 1
        if position + 1 < len(levels[split_level]):
            end = levels[split_level][position + 1][0]
        else:
            end = len(lines)

        path: list[str] = []
        for level in sorted(levels):
            if level >= split_level:
                continue
            for candidate_index, candidate in levels[level]:
                if candidate_index < index:
                    path.append(candidate)
                else:
                    break

        # drop the shallower headings, they are already in the path
        body_lines = [
            line
            for line in lines[start:end]
            if not HEADING_RE.match(line)
        ]
        blocks.append((heading, path, "\n".join(body_lines).strip()))

    return blocks


def pick_split_level(levels: dict[int, list[tuple[int, str]]]) -> int:
    """The deepest heading level that the document actually uses."""
    for level in sorted(levels, reverse=True):
        if len(levels[level]) >= 3:
            return level
    # nothing repeats, use the level with the most headings
    return max(levels, key=lambda level: (len(levels[level]), level))


def looks_hard_wrapped(lines: list[str]) -> bool:
    """True for PDF extractions where every line is wrapped and blank separated."""
    non_empty = [line for line in lines if line.strip()]
    if len(non_empty) < 12:
        return False
    short = sum(1 for line in non_empty if len(line.strip()) <= 70)
    blank_separated = sum(
        1
        for i in range(len(lines) - 1)
        if lines[i].strip() and not lines[i + 1].strip()
    )
    return short / len(non_empty) > 0.8 and blank_separated / len(non_empty) > 0.8


def unwrap_hard_wrapped(lines: list[str]) -> list[str]:
    """Join wrapped lines back into flowing paragraphs."""
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if HEADING_RE.match(stripped) or FENCE_RE.match(stripped):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(stripped)
            continue
        if stripped.startswith(("- ", "* ", "> ")):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(stripped)
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs


def slug_from_text(text: str, fallback: str) -> str:
    """Slug from the opening words of a passage."""
    first = text.strip().split("\n", 1)[0]
    first = re.sub(r"^#+\s*", "", first)
    words = " ".join(first.split()[:8])
    return slugify(words, fallback)


def looks_like_navigation(text: str) -> bool:
    """True for Wikipedia navigation boxes and project lists.

    Docling pulls those in as well, and they carry no knowledge at all.
    The bar is high on purpose: a chunk with a few wiki links in it is still
    good material.
    """
    lowered = text.lower()
    if "sister projects" in lowered[:300]:
        return True

    words = text.split()
    if not words:
        return False

    internal = re.findall(r"\]\(/wiki/(?:template|special|wikipedia):", lowered)
    if len(internal) > 8 and len(internal) / max(len(words), 1) > 0.15:
        return True

    links = re.findall(r"\[([^\]]*)\]\([^)]*\)", text)
    link_heavy = bool(len(links) > 20 and len(links) / max(len(words), 1) > 0.6)

    # a citation reference or a Commons list, nothing to learn from
    references = re.findall(r"\[\d+\]", text)
    reference_heavy = bool(
        len(references) > 3 and len(references) / max(len(words), 1) > 0.2
    )
    commons = "wikimedia commons has media related to" in lowered[:200]

    # newsletter and subscription footers
    footer = lowered[:400]
    subscribe = (
        "start your substack" in footer
        or "subscribe to our newsletter" in footer
        or "sign up for our newsletter" in footer
    )
    if subscribe and len(words) < 120:
        return True

    return link_heavy or reference_heavy or commons


def chunk_file(path: Path, target: str, category: str, seen: set[str]) -> list[Chunk]:
    """Chunk one source file into knowledge entries.

    `seen` is shared across every file that lands in the same output
    directory, otherwise two source files with the same heading overwrite
    each other.
    """
    raw = path.read_text(errors="replace")
    body, meta = strip_frontmatter(raw)
    source_url = meta.get("source_url", "")

    body_lines = clean_lines(body.splitlines())
    if looks_hard_wrapped(body_lines):
        body_lines = unwrap_hard_wrapped(body_lines)
    body = "\n".join(body_lines)

    chunks: list[Chunk] = []

    for heading, path_parts, text in split_headings(body):
        text = text.strip()
        if len(text) < MIN_CHUNK_CHARS:
            continue
        if looks_like_navigation(text):
            continue

        parts = split_long(text) if len(text) > MAX_CHUNK_CHARS else [text]

        for part in parts:
            if len(parts) > 1:
                slug = slug_from_text(part, path.stem)
            else:
                slug = slugify(heading or path.stem, path.stem)
            if slug in seen:
                suffix = 2
                while f"{slug}-{suffix}" in seen:
                    suffix += 1
                slug = f"{slug}-{suffix}"
            seen.add(slug)

            heading_path = path_parts + ([heading] if heading else [])
            chunks.append(
                Chunk(
                    heading=heading,
                    heading_path=heading_path,
                    text=part,
                    slug=slug,
                    source_file=str(path),
                    source_url=source_url,
                    target=target,
                    category=category,
                    word_count=len(part.split()),
                )
            )

    return chunks


SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_long(text: str) -> list[str]:
    """Break an oversized block into parts of at most MAX_CHUNK_CHARS."""
    lines = text.splitlines()
    table_rows = [line for line in lines if line.lstrip().startswith("|")]

    # a markdown table splits on rows, the words inside a row do not separate
    if table_rows and len(table_rows) > len(lines) * 0.6:
        return split_table(text, lines)

    sentences = SENTENCE_END.split(text)
    parts: list[str] = []
    current: list[str] = []
    size = 0

    for sentence in sentences:
        if len(sentence) > MAX_CHUNK_CHARS:
            if current:
                parts.append(" ".join(current))
                current = []
                size = 0
            parts.extend(split_words(sentence))
            continue
        if size + len(sentence) > MAX_CHUNK_CHARS and current:
            parts.append(" ".join(current))
            current = []
            size = 0
        current.append(sentence)
        size += len(sentence) + 1

    if current:
        parts.append(" ".join(current))

    return parts


def split_words(text: str) -> list[str]:
    """Cut a run of text that has no sentence or word boundaries."""
    words = text.split()
    parts: list[str] = []
    piece: list[str] = []
    size = 0

    for word in words:
        if len(word) > MAX_CHUNK_CHARS:
            # one unbroken run, cut it on character boundaries
            if piece:
                parts.append(" ".join(piece))
                piece = []
                size = 0
            for start in range(0, len(word), MAX_CHUNK_CHARS):
                parts.append(word[start : start + MAX_CHUNK_CHARS])
            continue

        if size + len(word) > MAX_CHUNK_CHARS and piece:
            parts.append(" ".join(piece))
            piece = []
            size = 0
        piece.append(word)
        size += len(word) + 1

    if piece:
        parts.append(" ".join(piece))

    return parts


def cut_long_line(line: str) -> list[str]:
    """Cut an oversized line, preferring the table cell boundary."""
    if len(line) <= MAX_CHUNK_CHARS:
        return [line]

    pieces: list[str] = []
    rest = line
    while len(rest) > MAX_CHUNK_CHARS:
        cut = rest.rfind("|", 0, MAX_CHUNK_CHARS)
        if cut <= 0:
            cut = MAX_CHUNK_CHARS
        pieces.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        pieces.append(rest)
    return pieces


def split_table(text: str, lines: list[str]) -> list[str]:
    """Split a markdown table into groups of rows."""
    parts: list[str] = []
    current: list[str] = []
    size = 0

    for line in lines:
        for piece in cut_long_line(line):
            if size + len(piece) > MAX_CHUNK_CHARS and current:
                parts.append("\n".join(current))
                current = []
                size = 0
            current.append(piece)
            size += len(piece) + 1

    if current:
        parts.append("\n".join(current))

    return parts


def collect_sources() -> list[tuple[Path, str, str]]:
    """Every source file with its target and category."""
    found: list[tuple[Path, str, str]] = []
    for group, (target, category) in SOURCE_GROUPS.items():
        folder = DATASET_DIR / group
        if not folder.exists():
            logger.warning("missing source folder: %s", folder)
            continue
        for path in sorted(folder.glob("*.md")):
            found.append((path, target, category))
    return found


def write_chunk(chunk: Chunk, generate: bool = False) -> None:
    """Write one knowledge entry to disk."""
    directory = KNOWLEDGE_DIR / chunk.target / chunk.category / chunk.slug
    directory.mkdir(parents=True, exist_ok=True)

    (directory / "content.md").write_text(chunk.text)

    metadata = f"""uri: {chunk.uri}
source: {chunk.source_file}
source_url: {chunk.source_url}
target: {chunk.target}
category: {chunk.category}
chunk_name: {chunk.slug}
heading: {chunk.heading}
heading_path: {" > ".join(chunk.heading_path)}
words: {chunk.word_count}
extracted: {datetime.now().strftime("%Y-%m-%d")}
tiers:
  l0:
    file: .abstract.md
  l1:
    file: .overview.md
  l2:
    file: content.md
"""
    (directory / ".metadata.yaml").write_text(metadata)

    if not generate:
        for name in (".abstract.md", ".overview.md"):
            path = directory / name
            if not path.exists():
                path.write_text("")


L0_PROMPT = """Write a concise essence of the text below, in 50 to 150 words.

Requirements:
- State the core claim or content of the text
- Name the people, places, dates and sources it involves
- Add a brief counterpoint if the text makes a contested claim
- Plain prose, no markdown headers, no preamble

Text:
{content}

Essence:"""

L1_PROMPT = """Write an insight summary of the text below, in 300 to 600 words.

Requirements:
- Use these markdown headers:

## Summary
- 3 to 5 bullet points covering the key points

## Why It Matters
- How this connects to the wider topic

## Counterpoints
- What an informed opponent would say

## Related Concepts
- 2 to 3 connected ideas

Write the summary itself. Do not describe the summary, do not list what it
would contain, do not mention that the text has headers or sections.

Text:
{content}

Summary:"""


async def summarize(
    chunks: list[Chunk],
    endpoint: str,
    model: str,
    concurrency: int,
    resume: bool = False,
) -> None:
    """Generate the L0 and L1 tiers for every chunk.

    Granite and LFM style models answer in two passes: the thinking tokens
    land in reasoning_content and only the final answer lands in content.
    The token budget therefore has to cover both, and an empty content with a
    finished reason means the budget was too small.
    """
    semaphore = asyncio.Semaphore(concurrency)
    done = 0
    failed = 0

    async with httpx.AsyncClient(timeout=600.0) as client:

        async def call(
            prompt: str,
            max_tokens: int,
            min_chars: int = 0,
            marker: str = "",
            retries: int = 2,
        ) -> str:
            """One chat call, with a bigger budget if the answer looks cut off.

            Granite and LFM answer in two passes. The thinking tokens land in
            reasoning_content and only the final answer lands in content. If
            the thinking eats the budget the answer comes back empty or
            truncated, so we retry with more room.
            """
            budget = max_tokens
            best = ""

            for _ in range(retries + 1):
                response = await client.post(
                    f"{endpoint.rstrip('/')}/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": budget + THINKING_BUDGET,
                        "temperature": 0.3,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                message = payload["choices"][0]["message"]
                content = (message.get("content") or "").strip()
                if not content:
                    content = (message.get("reasoning_content") or "").strip()

                if len(content) > len(best):
                    best = content

                if not content:
                    budget = budget * 2
                    continue
                if len(content) >= min_chars and (not marker or marker in content):
                    return content

                budget = budget * 2

            # no answer had the expected shape, but a long one is still usable
            if len(best) >= min_chars:
                return best

            raise RuntimeError(
                f"no usable answer after {retries + 1} tries: {len(best)} chars"
            )

        async def handle(chunk: Chunk) -> None:
            nonlocal done, failed
            async with semaphore:
                directory = KNOWLEDGE_DIR / chunk.target / chunk.category / chunk.slug
                abstract_path = directory / ".abstract.md"
                overview_path = directory / ".overview.md"

                if (
                    resume
                    and abstract_path.exists()
                    and overview_path.exists()
                    and abstract_path.stat().st_size > 200
                    and overview_path.stat().st_size > 500
                ):
                    done += 1
                    return

                body = chunk.text[:8000]
                retries = 2
                for attempt in range(retries + 1):
                    try:
                        l0, l1 = await asyncio.gather(
                            call(L0_PROMPT.format(content=body), 1500, min_chars=150),
                            call(
                                L1_PROMPT.format(content=body),
                                3000,
                                min_chars=400,
                                marker="## Summary",
                            ),
                        )
                        abstract_path.write_text(l0)
                        overview_path.write_text(l1)
                        break
                    except Exception as exc:
                        if attempt == retries:
                            logger.error("failed to summarize %s: %s", chunk.slug, exc)
                            failed += 1
                        else:
                            await asyncio.sleep(3 * (attempt + 1))
                done += 1
                if done % 10 == 0:
                    logger.info("summarized %d/%d (failed %d)", done, len(chunks), failed)

        await asyncio.gather(*(handle(chunk) for chunk in chunks))
    logger.info("summarize finished: %d done, %d failed", done, failed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the knowledge tier")
    parser.add_argument("--summarize", action="store_true", help="also generate L0 and L1")
    parser.add_argument("--target", help="only this worldview")
    parser.add_argument("--category", help="only this category")
    parser.add_argument("--endpoint", default=os.environ.get("LLM_API_BASE", "http://localhost:11433/v1"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", "granite-4.0-h-tiny"))
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--resume", action="store_true", help="skip chunks that are done")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sources = collect_sources()
    logger.info("found %d source files", len(sources))

    all_chunks: list[Chunk] = []
    seen: dict[tuple[str, str], set[str]] = {}
    for path, target, category in sources:
        if args.target and target != args.target:
            continue
        if args.category and category != args.category:
            continue
        key = (target, category)
        chunks = chunk_file(path, target, category, seen.setdefault(key, set()))
        logger.info("%-52s %3d chunks", path, len(chunks))
        all_chunks.extend(chunks)

    total_words = sum(chunk.word_count for chunk in all_chunks)
    logger.info(
        "total %d chunks, %d words, ~%d tokens",
        len(all_chunks),
        total_words,
        total_words * 4 // 3,
    )

    if args.dry_run:
        for chunk in all_chunks[:20]:
            print(f"{chunk.target}/{chunk.category}/{chunk.slug} ({chunk.word_count} words)")
        return

    for chunk in all_chunks:
        write_chunk(chunk)

    logger.info("wrote %d knowledge entries", len(all_chunks))

    if args.summarize:
        logger.info("summarizing with %s at %s", args.model, args.endpoint)
        asyncio.run(
            summarize(
                all_chunks,
                args.endpoint,
                args.model,
                args.concurrency,
                resume=args.resume,
            )
        )
        logger.info("done")


if __name__ == "__main__":
    main()
