#!/usr/bin/env python3
"""
Embedding Model Benchmark for parallax.observer

Tests Nomic ModernBERT embeddings with:
- 768 dimension (full)
- 256 dimension (truncated)
- Single and batch encoding
- Similarity computation

Usage:
    HF_TOKEN=your_token conda run -n parallax.observer python benchmark.py
"""

import os
import sys
import gc
import time
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

# Configuration
MODEL_ID = "nomic-ai/modernbert-embed-base"
DIMENSIONS = [768, 256]
BATCH_SIZES = [1, 32, 64]

# Test documents (persuasion-themed)
TEST_DOCUMENTS = [
    "search_document: Water always finds its level. This is proof the Earth is flat.",
    "search_document: The horizon appears flat from any altitude, even from planes.",
    "search_document: NASA photos are computer generated imagery, not real photographs.",
    "search_document: Gravity is just a theory. Density and buoyancy explain everything.",
    "search_document: Ships disappear over the horizon due to perspective, not curvature.",
    "search_document: The Bedford Level experiment proved water is flat over 6 miles.",
    "search_document: Antarctica is not a continent, it's an ice wall surrounding us.",
    "search_document: Flight paths make more sense on a flat Earth map.",
    "search_document: The Foucault pendulum proves Earth rotates, but could be fake.",
    "search_document: Lunar eclipses are caused by something else, not Earth's shadow.",
    "search_document: Stars rotate around Polaris, proving we're the center.",
    "search_document: No one has circumnavigated Earth north to south.",
    "search_document: The vanishing point makes things disappear bottom-first.",
    "search_document: Surveyors and engineers never account for curvature.",
    "search_document: The Coriolis effect is explained by the firmament above.",
    "search_document: Time zones work on a flat Earth with a spotlight sun.",
    "search_document: GPS works through ground-based towers, not satellites.",
    "search_document: The moon landing was filmed in a studio on Earth.",
    "search_document: Space agencies worldwide are part of the conspiracy.",
    "search_document: The firmament is a dome above the flat Earth plane.",
    "search_document: Admiral Byrd found land beyond Antarctica.",
    "search_document: The UN flag shows the true flat Earth map.",
    "search_document: Curved water has never been demonstrated experimentally.",
    "search_document: Fish eye lenses make horizons appear curved in photos.",
    "search_document: The atmosphere refracts light to create illusion of sunset.",
    "search_document: Circumnavigation is just going in a circle on flat plane.",
    "search_document: The southern cross constellation proves southern hemisphere exists.",
    "search_document: Eric Dubay compiled 200 proofs the Earth is flat.",
    "search_document: Operation Highjump discovered the ice wall.",
    "search_document: NASA loses original footage of moon missions.",
    "search_document: The sun is much closer and smaller than claimed.",
    "search_document: Crepuscular rays prove the sun is nearby.",
]

TEST_QUERY = "search_query: Why do ships disappear over the horizon?"


@dataclass
class EmbeddingResult:
    """Results for a single embedding test"""
    dimension: int
    load_time_sec: float
    memory_mb: float
    single_embedding_ms: float
    batch_results: List[Dict[str, Any]]
    similarity_time_ms: float
    success: bool
    error: str = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_gpu_memory_mb() -> float:
    """Get current GPU memory usage in MB"""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 * 1024)
    except:
        pass
    return 0.0


def clear_gpu_memory():
    """Clear GPU memory"""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except:
        pass
    gc.collect()


def benchmark_dimension(dimension: int) -> EmbeddingResult:
    """Benchmark embedding model with specific dimension"""
    print(f"\n{'='*60}")
    print(f" Testing Dimension: {dimension}")
    print(f"{'='*60}")
    
    load_time = 0.0
    memory_mb = 0.0
    single_time = 0.0
    batch_results = []
    similarity_time = 0.0
    
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        # Clear GPU before loading
        print("\n[1/5] Clearing GPU memory...")
        clear_gpu_memory()
        
        # Load model
        print(f"\n[2/5] Loading model (dimension={dimension})...")
        start_time = time.time()
        
        if dimension == 768:
            model = SentenceTransformer(MODEL_ID)
        else:
            model = SentenceTransformer(MODEL_ID, truncate_dim=dimension)
        
        load_time = time.time() - start_time
        memory_mb = get_gpu_memory_mb()
        print(f"      Loaded in {load_time:.2f}s, memory: {memory_mb:.1f} MB")
        
        # Single embedding
        print(f"\n[3/5] Testing single embedding...")
        start_time = time.time()
        embedding = model.encode(TEST_QUERY)
        single_time = (time.time() - start_time) * 1000
        print(f"      Single embedding: {single_time:.2f}ms, shape: {embedding.shape}")
        
        # Batch embeddings at different sizes
        print(f"\n[4/5] Testing batch embeddings...")
        for batch_size in BATCH_SIZES:
            docs = TEST_DOCUMENTS[:batch_size]
            if len(docs) < batch_size:
                docs = docs * (batch_size // len(docs) + 1)
                docs = docs[:batch_size]
            
            start_time = time.time()
            embeddings = model.encode(docs, batch_size=batch_size)
            batch_time = (time.time() - start_time) * 1000
            
            result = {
                "batch_size": batch_size,
                "time_ms": batch_time,
                "time_per_doc_ms": batch_time / batch_size,
                "shape": list(embeddings.shape),
            }
            batch_results.append(result)
            print(f"      Batch {batch_size}: {batch_time:.2f}ms ({batch_time/batch_size:.2f}ms/doc)")
        
        # Similarity computation
        print(f"\n[5/5] Testing similarity computation...")
        query_emb = model.encode(TEST_QUERY)
        doc_embs = model.encode(TEST_DOCUMENTS[:10])
        
        start_time = time.time()
        similarities = model.similarity(query_emb, doc_embs)
        similarity_time = (time.time() - start_time) * 1000
        print(f"      Similarity (1 query × 10 docs): {similarity_time:.2f}ms")
        print(f"      Top 3 scores: {similarities[0][:3].tolist()}")
        
        # Cleanup
        del model
        clear_gpu_memory()
        
        return EmbeddingResult(
            dimension=dimension,
            load_time_sec=load_time,
            memory_mb=memory_mb,
            single_embedding_ms=single_time,
            batch_results=batch_results,
            similarity_time_ms=similarity_time,
            success=True,
        )
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        clear_gpu_memory()
        
        return EmbeddingResult(
            dimension=dimension,
            load_time_sec=load_time,
            memory_mb=memory_mb,
            single_embedding_ms=single_time,
            batch_results=batch_results,
            similarity_time_ms=similarity_time,
            success=False,
            error=str(e),
        )


def print_results_table(results: List[EmbeddingResult]):
    """Print results in a formatted table"""
    print(f"\n{'='*70}")
    print(" EMBEDDING BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"{'Dim':<6} {'Load(s)':<10} {'Mem(MB)':<10} {'Single(ms)':<12} {'Status'}")
    print(f"{'-'*70}")
    
    for r in results:
        status = "✅" if r.success else "❌"
        print(f"{r.dimension:<6} {r.load_time_sec:<10.2f} {r.memory_mb:<10.1f} {r.single_embedding_ms:<12.2f} {status}")
    
    # Batch results
    print(f"\n{'='*70}")
    print(" BATCH PERFORMANCE")
    print(f"{'='*70}")
    print(f"{'Dim':<6} {'Batch':<8} {'Time(ms)':<12} {'Per Doc(ms)':<12}")
    print(f"{'-'*70}")
    
    for r in results:
        if r.success:
            for br in r.batch_results:
                print(f"{r.dimension:<6} {br['batch_size']:<8} {br['time_ms']:<12.2f} {br['time_per_doc_ms']:<12.2f}")
    
    print(f"{'='*70}\n")


def main():
    print("\n" + "="*60)
    print(" Embedding Model Benchmark")
    print(" parallax.observer")
    print("="*60)
    print(f"\nModel: {MODEL_ID}")
    print(f"Dimensions to test: {DIMENSIONS}")
    print(f"Batch sizes: {BATCH_SIZES}")
    
    # Check HF token
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        print(f"HF_TOKEN: {hf_token[:10]}...")
    else:
        print("HF_TOKEN: not set (may need for gated models)")
    
    results: List[EmbeddingResult] = []
    
    # Run benchmark for each dimension
    for dim in DIMENSIONS:
        result = benchmark_dimension(dim)
        results.append(result)
    
    # Print summary
    print_results_table(results)
    
    # Save results
    output_file = Path(__file__).parent.parent / "benchmark_embeddings_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "model": MODEL_ID,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [r.to_dict() for r in results]
        }, f, indent=2)
    print(f"Results saved to: {output_file}")
    
    # Final GPU state
    print("\nFinal GPU state:")
    try:
        import torch
        if torch.cuda.is_available():
            total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            allocated = torch.cuda.memory_allocated() / (1024**3)
            print(f"  Total: {total:.2f} GiB")
            print(f"  Allocated: {allocated:.2f} GiB")
            print(f"  Free: {total - allocated:.2f} GiB")
    except:
        print("  GPU not available")
    
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
