#!/usr/bin/env python3
"""
Turn the reference images into knowledge entries.

Each image becomes a wisdom, the same as a text one, with the caption as the
content and the picture alongside it. The interface can then show the actual
Ferguson map next to the claim that is being argued about.

The image itself is embedded with the vision encoder of EmbeddingGemma 2, so
the vector is there if we ever want to search by picture. The entry is
indexed by its caption, which is how a human would look for it anyway.

The two sides do not quite speak the same dialect. OpenViking sends the
content parts the way the OpenAI API does, and llama.cpp wants the text in
`input` and the pictures in a separate `multimodal_data` array. So the image
is embedded here, and the caption goes to the corpus.

Usage:
    python scripts/embed_images.py --dry-run
    python scripts/embed_images.py
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

IMAGES_DIR = Path("dataset/images")
FACTS_DIR = Path("facts/knowledge")
MODEL = "embeddinggemma-2"


def load_captions() -> dict[str, dict[str, str]]:
    """The caption of every image, from the download list."""
    sys.path.insert(0, str(Path(__file__).parent))
    from download_images import IMAGE_SOURCES

    return {
        f"{name}": {"worldview": worldview, "caption": caption}
        for name, _title, worldview, caption in IMAGE_SOURCES
    }


def embed_image(
    client: httpx.Client,
    endpoint: str,
    image_path: Path,
    caption: str,
) -> list[float] | None:
    """The embedding of one image, text and picture together."""
    payload = image_path.read_bytes()
    encoded = base64.b64encode(payload).decode()

    # llama.cpp wants the text in input and the pictures in multimodal_data
    body = {
        "model": MODEL,
        "input": caption,
        "multimodal_data": [encoded],
    }

    try:
        response = client.post(f"{endpoint.rstrip('/')}/embedding", json=body, timeout=300.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning("could not embed %s: %s", image_path.name, exc)
        return None

    vector = data[0]["embedding"] if isinstance(data, list) else data.get("embedding", [])
    if vector and isinstance(vector[0], list):
        # the multimodal path nests the vector one level deeper
        vector = vector[0]

    return vector


L1_PROMPT = """You are writing the short description of an image for a knowledge base.

The image is called {name}. It belongs to the {worldview} point of view on the
shape of the Earth. What it shows: {caption}

Write two or three sentences. Say what the image is, what it is being used to
argue, and what a reader should notice about it. Plain prose, no headers, no
bullet points."""


def write_overview(
    client: httpx.Client,
    endpoint: str,
    model: str,
    image_path: Path,
    worldview: str,
    caption: str,
    directory: Path,
) -> None:
    """The L0 and the L1 of an image."""
    (directory / ".abstract.md").write_text(caption)

    prompt = L1_PROMPT.format(
        name=image_path.stem.replace("-", " "),
        worldview=worldview,
        caption=caption,
    )
    try:
        response = client.post(
            f"{endpoint.rstrip('/')}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.4,
                "stream": False,
            },
            timeout=300.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"].get("content") or ""
        if not content:
            content = caption
    except Exception as exc:
        logger.warning("could not describe %s: %s", image_path.name, exc)
        content = caption

    (directory / ".overview.md").write_text(content.strip())


def write_entry(
    image_path: Path,
    worldview: str,
    caption: str,
    vector: list[float] | None,
    source_title: str = "",
) -> Path:
    """Write the knowledge entry for one image."""
    directory = FACTS_DIR / worldview / "images" / image_path.stem
    directory.mkdir(parents=True, exist_ok=True)

    (directory / "content.md").write_text(
        f"# {image_path.stem}\n\n{caption}\n"
    )

    # the picture lives with the entry, so the interface can show it
    shutil.copy2(image_path, directory / image_path.name)

    if vector:
        # the vector lives outside the corpus. Inside it, the server would
        # try to embed seventeen kilobytes of json and reject it
        vectors = FACTS_DIR.parent / "images" / worldview
        vectors.mkdir(parents=True, exist_ok=True)
        (vectors / f"{image_path.stem}.embedding.json").write_text(
            json.dumps({"model": MODEL, "dimension": len(vector), "vector": vector})
        )

    metadata = f"""uri: viking://resources/knowledge/{worldview}/images/{image_path.stem}
source: {image_path}
source_url: {source_title}
target: {worldview}
category: images
chunk_name: {image_path.stem}
heading: {image_path.stem}
image: {image_path.name}
words: {len(caption.split())}
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

    return directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed the reference images")
    parser.add_argument("--endpoint", default="http://localhost:11433")
    parser.add_argument("--model", default="granite-4.0-h-tiny")
    parser.add_argument("--images-dir", type=Path, default=IMAGES_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    captions = load_captions()

    images = sorted(args.images_dir.rglob("*.jpg")) + sorted(args.images_dir.rglob("*.png"))
    if not images:
        logger.error("no images, run scripts/download_images.py first")
        return 1

    logger.info("%d images to embed", len(images))

    with httpx.Client(timeout=300.0) as client:
        for image_path in images:
            worldview = image_path.parent.name
            info = captions.get(image_path.stem, {})
            worldview = info.get("worldview", worldview)
            caption = info.get("caption", image_path.stem.replace("-", " "))

            if args.dry_run:
                logger.info("would embed %s as %s/%s", image_path.name, worldview, caption)
                continue

            vector = embed_image(client, args.endpoint, image_path, caption)
            if vector is None:
                logger.warning("skipped %s", image_path.name)
                continue

            directory = write_entry(image_path, worldview, caption, vector)
            write_overview(
                client,
                args.endpoint,
                args.model,
                image_path,
                worldview,
                caption,
                directory,
            )
            logger.info("wrote %s with a %d dimension vector", directory, len(vector))

    logger.info("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
