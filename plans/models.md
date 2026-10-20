# Models: LLM, VLM, and Embeddings

> AI models for parallax.observer - Ollama for LLM/VLM, Infinity for embeddings

## Overview

parallax.observer uses **Ollama** for all LLM/VLM inference and **Infinity** for embeddings.

| Component | Technology | Port | Purpose |
|-----------|------------|------|---------|
| LLM/VLM Inference | Ollama (Docker) | 11433 | Text generation, vision chat |
| Text Embeddings | Infinity (Docker) | 7997 | Semantic search, RAG |
| Image Embeddings | Infinity (Docker) | 7997 | Image search, CLIP-style |

---

## Tested Models

### LLM/VLM Models (Ollama, Q4_K_M Quantization)

| Model | Type | Size | Load | Throughput | Latency | Use Case |
|-------|------|------|------|------------|---------|----------|
| **granite3.3:2b** | Reasoning | 1.5 GB | 1.4s | **154.7 tok/s** | 1332ms | Fast reasoning, thinking mode |
| **granite4:tiny-h** | MoE | 4.0 GB | 2.6s | 124.8 tok/s | 1113ms | Long context (128K), multilingual |
| **granite4:micro-h** | Hybrid | 2.0 GB | 1.8s | 107.6 tok/s | 1451ms | Lightweight, fast loading |
| **qwen3-vl:2b** | Vision | 1.9 GB | ~3s | ~40 tok/s | ~6s | Image analysis, OCR |

### Embedding Models (Infinity)

| Model | Type | Dimensions | Use Case |
|-------|------|------------|----------|
| **nomic-ai/modernbert-embed-base** | Text | 768 | Semantic search, RAG |
| **google/siglip-so400m-patch14-384** | Image | 384 | Image search, text-image matching |

### Model Details

#### Granite 3.3 2B (Reasoning)

| Property | Value |
|----------|-------|
| Ollama Tag | `granite3.3:2b` |
| Parameters | 2.5B |
| Context | 128K tokens |
| Quantization | Q4_K_M |
| License | Apache 2.0 |

**Thinking Mode:**
```bash
curl -X POST http://localhost:11433/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite3.3:2b",
    "messages": [
      {"role": "control", "content": "thinking"},
      {"role": "user", "content": "Prove the Earth is round using physics."}
    ]
  }'
```

#### Granite 4.0 Tiny-H (MoE)

| Property | Value |
|----------|-------|
| Ollama Tag | `granite4:tiny-h` |
| Total Parameters | 6.9B |
| Active Parameters | ~1B (MoE) |
| Context | 128K tokens |
| Quantization | Q4_K_M |
| License | Apache 2.0 |

Mixture-of-Experts architecture - only 1B params active per inference for memory efficiency.

#### Granite 4.0 Micro-H (Hybrid Mamba-2)

| Property | Value |
|----------|-------|
| Ollama Tag | `granite4:micro-h` |
| Parameters | 3.2B |
| Context | 128K tokens |
| Quantization | Q4_K_M |
| License | Apache 2.0 |

Hybrid architecture with Mamba-2 layers for efficient long-context handling.

#### Qwen3-VL 2B (Vision-Language)

| Property | Value |
|----------|-------|
| Ollama Tag | `qwen3-vl:2b` |
| Parameters | 2B |
| Context | 32K tokens |
| Capabilities | Image understanding, OCR |

**Vision Test Results:**
- Correctly reads text from images
- Identifies objects, symbols, colors
- Describes visual composition

---

## Ollama Infrastructure

### Docker Setup

Location: `docker/`

```yaml
# docker/docker-compose.yml
services:
  parallax-ollama:
    image: ollama/ollama:latest
    ports:
      - "11433:11434"
    environment:
      OLLAMA_FLASH_ATTENTION: 1
      OLLAMA_KV_CACHE_TYPE: q8_0
      OLLAMA_CONTEXT_LENGTH: 128000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Start Ollama

```bash
# Start everything (includes Ollama)
docker/up.sh

# Or start just Ollama
docker/up.sh ollama
```

### Pull Models

```bash
# Text models (Q4_K_M from Ollama library)
ollama pull granite4:micro-h
ollama pull granite4:tiny-h
ollama pull granite3.3:2b

# Vision model
ollama pull qwen3-vl:2b
```

### API Usage

**Generate:**
```bash
curl http://localhost:11433/api/generate -d '{
  "model": "granite3.3:2b",
  "prompt": "Why is the Earth round?",
  "stream": false
}'
```

**Chat:**
```bash
curl http://localhost:11433/api/chat -d '{
  "model": "granite3.3:2b",
  "messages": [{"role": "user", "content": "Hello!"}]
}'
```

**Vision (with image):**
```python
import base64
import requests

with open("image.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = requests.post("http://localhost:11433/api/generate", json={
    "model": "qwen3-vl:2b",
    "prompt": "What do you see in this image?",
    "images": [image_b64],
    "stream": False,
})
print(response.json()["response"])
```

### Model Management

```bash
# List models
curl http://localhost:11433/api/tags

# Unload model from GPU
curl http://localhost:11433/api/generate -d '{
  "model": "granite3.3:2b",
  "keep_alive": 0
}'

# Delete model
ollama rm granite3.3:2b
```

---

## Embeddings

See [plans/embeddings.md](embeddings.md) for full documentation.

### Quick Reference

| Property | Value |
|----------|-------|
| Model | `nomic-ai/modernbert-embed-base` |
| Dimensions | 768 (supports Matryoshka: 256, 512) |
| Context | 8192 tokens |
| License | Apache 2.0 |

### Usage (via Infinity API)

```python
import httpx

INFINITY_URL = "http://localhost:7997/v1/embeddings"
TEXT_MODEL = "nomic-ai/modernbert-embed-base"

def get_embedding(text: str, dimension: int | None = None) -> list[float]:
    payload = {"model": TEXT_MODEL, "input": text}
    if dimension:
        payload["dimensions"] = dimension
    response = httpx.post(INFINITY_URL, json=payload)
    return response.json()["data"][0]["embedding"]

# Query
query_embedding = get_embedding("search_query: Why is the earth flat?")

# Document
doc_embedding = get_embedding("search_document: Water always finds its level.")

# With dimension truncation
embedding_256 = get_embedding("search_query: text", dimension=256)
```

---

## Configuration

### Environment Variables

```bash
# Ollama
OLLAMA_HOST=http://localhost:11433

# Embeddings
EMBEDDING_MODEL=nomic-ai/modernbert-embed-base
EMBEDDING_DIMENSION=768
```

### Project Config

```yaml
# config/models.yaml

inference:
  engine: ollama
  host: http://localhost:11433
  default_model: granite3.3:2b

models:
  granite3.3:2b:
    type: reasoning
    context: 128000
    thinking_mode: true
    
  granite4:tiny-h:
    type: moe
    context: 128000
    
  granite4:micro-h:
    type: hybrid
    context: 128000
    
  qwen3-vl:2b:
    type: vlm
    context: 32000

embeddings:
  model: nomic-ai/modernbert-embed-base
  dimension: 768
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     parallax.observer                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Ollama (Docker)                          │  │
│  │              Port: 11433                              │  │
│  │                                                       │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │ granite3.3  │ │ granite4    │ │ qwen3-vl    │    │  │
│  │  │ :2b         │ │ :tiny-h     │ │ :2b         │    │  │
│  │  │ Reasoning   │ │ MoE, 128K   │ │ Vision      │    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  │                                                       │  │
│  │  Flash Attention: ON | KV Cache: q8_0               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Embeddings                               │  │
│  │              nomic-ai/modernbert-embed-base           │  │
│  │              768 dimensions | 8K context              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Benchmark Files

- `investigations/ollama/benchmark.py` - Performance benchmark script
- `investigations/benchmark_ollama_results.json` - Full benchmark results
- `investigations/ollama/test_vlm.py` - Vision model test script

---

## Wisdom Extraction Pipeline Models

The wisdom extraction pipeline (`scripts/expand_enrichment.py`) uses a simplified 2-model strategy:

| Task | Model | Type | VRAM | Purpose |
|------|-------|------|------|---------|
| **L0 Essence** | `granite4:tiny-h` | MoE | 5.6 GB | Fast summarization |
| **L1 Insight** | `granite4:tiny-h` | MoE | (shared) | Context, hooks, arguments |
| **L2 Depth** | `granite3.3:2b` | Thinking | 1.5 GB | Rich "fabulous" origin stories |

**Total VRAM:** ~7.1 GB when both models loaded

### Model Selection Rationale

- **granite4:tiny-h for L0/L1**: MoE architecture provides excellent throughput while sharing the same model reduces memory overhead
- **granite3.3:2b for L2**: Thinking/reasoning model produces the engaging narrative content

### Model Management

The pipeline automatically:
1. Preloads required models at startup
2. Unloads unused models (e.g., granite4:micro-h)
3. Monitors VRAM via Ollama `/api/ps` endpoint

```bash
# Check loaded models
curl -s http://localhost:11433/api/ps | jq '.models[].name'

# Manual unload
curl -X POST http://localhost:11433/api/generate -d '{
  "model": "granite4:micro-h",
  "keep_alive": 0
}'
```

---

## Related Files

- [plans/embeddings.md](embeddings.md) - Embedding model documentation
- [plans/memory.md](memory.md) - OpenViking memory system
- [docker/](../docker/) - Docker configuration
