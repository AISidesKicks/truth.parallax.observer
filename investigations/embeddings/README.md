# Embedding Model Benchmark

Tests Nomic ModernBERT embedding model for parallax.observer.

## What It Tests

- **Dimension comparison**: 768 (full) vs 256 (truncated)
- **Single embedding latency**
- **Batch processing speed** (1, 32, 64 documents)
- **Similarity computation**
- **Memory usage**

## Prerequisites

```bash
# Activate conda environment
conda activate parallax.observer

# Set HF token (if needed)
export HF_TOKEN=your_token_here
```

## Usage

```bash
# Run benchmark
HF_TOKEN=$(grep HF_TOKEN ../../.env | cut -d= -f2) \
  conda run -n parallax.observer python benchmark.py
```

## Output

Results saved to `../benchmark_embeddings_results.json`:

```json
{
  "model": "nomic-ai/modernbert-embed-base",
  "timestamp": "2025-01-19 18:00:00",
  "results": [
    {
      "dimension": 768,
      "load_time_sec": 5.0,
      "memory_mb": 512.0,
      "single_embedding_ms": 2.5,
      "batch_results": [...],
      "similarity_time_ms": 0.5,
      "success": true
    }
  ]
}
```

## Test Documents

Uses 32 persuasion-themed documents about Flat Earth theories, plus queries for similarity testing.

## Metrics Explained

| Metric | Description |
|--------|-------------|
| `load_time_sec` | Time to load model into memory |
| `memory_mb` | GPU memory allocated after load |
| `single_embedding_ms` | Latency for one embedding |
| `batch_results` | Performance at different batch sizes |
| `similarity_time_ms` | Time to compute query vs 10 docs |

## Related

- [plans/embeddings.md](../../plans/embeddings.md) - Embedding model documentation
- [plans/memory.md](../../plans/memory.md) - OpenViking integration
