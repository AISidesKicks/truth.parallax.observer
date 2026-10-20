#!/usr/bin/env python3
"""
Test OpenViking retrieval with semantic search queries.

Usage:
    python scripts/test_viking.py
"""

import json
import math
from pathlib import Path

VIKING_DIR = Path("memory/viking/resources/enrichment")


def load_embedding(embedding_file: Path) -> list[float]:
    """Load embedding from JSON file."""
    with open(embedding_file) as f:
        return json.load(f)["embedding"]


def get_query_embedding(query: str) -> list[float]:
    """Get embedding for query from Infinity server."""
    import requests
    
    response = requests.post(
        "http://localhost:7997/embeddings",
        json={
            "model": "nomic-ai/nomic-embed-text-v1.5",
            "input": [f"search_query: {query}"],
        },
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot_product / (norm_a * norm_b)


def search(query: str, top_k: int = 5, target: str | None = None) -> list[dict]:
    """Search for similar wisdoms."""
    query_embedding = get_query_embedding(query)
    
    results = []
    
    search_paths = []
    if target:
        search_paths.append(VIKING_DIR / target)
    else:
        search_paths.append(VIKING_DIR)
    
    for base_path in search_paths:
        for embedding_file in base_path.rglob(".embedding.json"):
            wisdom_dir = embedding_file.parent
            wisdom_name = wisdom_dir.name
            
            parts = str(wisdom_dir).split("/")
            target_name = parts[-3]
            category = parts[-2]
            
            embedding = load_embedding(embedding_file)
            score = cosine_similarity(query_embedding, embedding)
            
            abstract_file = wisdom_dir / ".abstract"
            abstract = abstract_file.read_text()[:200] if abstract_file.exists() else ""
            
            results.append({
                "name": wisdom_name,
                "target": target_name,
                "category": category,
                "score": score,
                "abstract": abstract,
            })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def main():
    test_queries = [
        "NASA fake photos CGI",
        "water finds its level",
        "ice wall Antarctica",
        "gravity is a theory",
        "ships disappearing hull first",
        "airplane windows curved",
        "flat earth map UN logo",
        "moon landing hoax",
        "GPS cell towers",
        "horizon flat from plane",
        "Antarctic Treaty conspiracy",
        "density buoyancy gravity",
        "amateur balloon footage",
        "Chicago skyline Lake Michigan",
        "Coriolis effect sniper",
        "sun local small",
        "eclipses black sun",
        "firmament dome rockets",
        "Bedford Level experiment",
        "Michelson Morley experiment",
    ]
    
    print("=" * 70)
    print(" OpenViking Semantic Search Test")
    print("=" * 70)
    print(f"\nTotal embeddings: {len(list(VIKING_DIR.rglob('.embedding.json')))}")
    print("\nRunning 20 test queries...\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i:2d}] Query: '{query}'")
        print("-" * 50)
        
        results = search(query, top_k=3)
        
        for j, r in enumerate(results, 1):
            print(f"  {j}. [{r['score']:.4f}] {r['target']}/{r['category']}/{r['name']}")
            if j == 1 and r['abstract']:
                print(f"     Abstract: {r['abstract'][:100]}...")
    
    print("\n" + "=" * 70)
    print(" Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
