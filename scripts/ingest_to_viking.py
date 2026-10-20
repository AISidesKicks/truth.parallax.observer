#!/usr/bin/env python3
"""
Ingest wisdoms from facts/enrichment to memory/viking for OpenViking.

Usage:
    python scripts/ingest_to_viking.py [--dry-run]
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

FACTS_DIR = Path("facts/enrichment")
MEMORY_DIR = Path("memory/viking/resources/enrichment")


def get_embedding(text: str) -> list[float]:
    """Get embedding from Infinity server."""
    import requests
    
    response = requests.post(
        "http://localhost:7997/embeddings",
        json={
            "model": "nomic-ai/nomic-embed-text-v1.5",
            "input": [f"search_document: {text}"],
        },
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def ingest_wisdom(wisdom_dir: Path, target: str, category: str, dry_run: bool = False) -> dict:
    """Ingest a single wisdom to OpenViking format."""
    wisdom_name = wisdom_dir.name
    
    l0_file = wisdom_dir / "l0.abstract"
    l1_file = wisdom_dir / "l1.overview"
    l2_file = wisdom_dir / "l2.content.md"
    meta_file = wisdom_dir / ".metadata.yaml"
    
    if not all(f.exists() for f in [l0_file, l1_file, l2_file]):
        return {"status": "skipped", "reason": "missing files"}
    
    l0_content = l0_file.read_text().strip()
    l1_content = l1_file.read_text().strip()
    l2_content = l2_file.read_text().strip()
    
    output_dir = MEMORY_DIR / target / category / wisdom_name
    
    if dry_run:
        return {"status": "dry_run", "path": str(output_dir)}
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    (output_dir / ".abstract").write_text(l0_content)
    (output_dir / ".overview").write_text(l1_content)
    (output_dir / "content.md").write_text(l2_content)
    
    if meta_file.exists():
        shutil.copy(meta_file, output_dir / ".metadata.yaml")
    
    combined_text = f"{l0_content}\n\n{l1_content}\n\n{l2_content}"
    embedding = get_embedding(combined_text[:8000])
    
    embedding_file = output_dir / ".embedding.json"
    embedding_file.write_text(json.dumps({
        "model": "nomic-ai/nomic-embed-text-v1.5",
        "dimension": len(embedding),
        "generated": datetime.now().isoformat(),
        "embedding": embedding,
    }))
    
    return {"status": "ingested", "path": str(output_dir), "embedding_dim": len(embedding)}


def main():
    parser = argparse.ArgumentParser(description="Ingest wisdoms to OpenViking")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()
    
    print("=" * 60)
    print(" OpenViking Ingestion")
    print("=" * 60)
    
    if args.dry_run:
        print("DRY RUN MODE - no files will be written\n")
    
    stats = {
        "total": 0,
        "ingested": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    targets = ["flat-earth", "spherical-earth", "discworld", "norse"]
    categories = ["misleading-facts", "catchphrases", "quotes"]
    
    for target in targets:
        for category in categories:
            source_dir = FACTS_DIR / target / category
            if not source_dir.exists():
                continue
            
            wisdoms = [d for d in source_dir.iterdir() if d.is_dir() and (d / ".metadata.yaml").exists()]
            
            if not wisdoms:
                continue
            
            print(f"\n{target}/{category}: {len(wisdoms)} wisdoms")
            
            for wisdom_dir in wisdoms:
                stats["total"] += 1
                try:
                    result = ingest_wisdom(wisdom_dir, target, category, args.dry_run)
                    if result["status"] == "ingested" or result["status"] == "dry_run":
                        stats["ingested"] += 1
                        print(f"  ✓ {wisdom_dir.name}")
                    else:
                        stats["skipped"] += 1
                        print(f"  - {wisdom_dir.name}: {result.get('reason', 'unknown')}")
                except Exception as e:
                    stats["errors"] += 1
                    print(f"  ✗ {wisdom_dir.name}: {e}")
    
    print("\n" + "=" * 60)
    print(f" Total: {stats['total']}")
    print(f" Ingested: {stats['ingested']}")
    print(f" Skipped: {stats['skipped']}")
    print(f" Errors: {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
