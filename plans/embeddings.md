# Embeddings: Infinity Server

> High-throughput embedding server with OpenAI-compatible API for text and image embeddings

## Overview

parallax.observer uses **Infinity** as a dedicated embedding server, providing:

- **Text embeddings** via `nomic-ai/modernbert-embed-base`
- **Image embeddings** via `google/siglip-so400m-patch14-384`
- **OpenAI-compatible REST API** on port 7997

```
┌─────────────────────────────────────────────────────────────────┐
│                     Infinity Server                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐│
│  │  Text Embeddings    │    │  Image Embeddings              ││
│  │  modernbert-embed   │    │  siglip-so400m                 ││
│  │  768 dimensions     │    │  384 dimensions                ││
│  │  8K context         │    │  image + text search           ││
│  └─────────────────────┘    └─────────────────────────────────┘│
│                                                                  │
│  OpenAI-Compatible API: http://localhost:7997/v1/embeddings    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Models

### Text Embeddings: Nomic ModernBERT

| Property | Value |
|----------|-------|
| Model | `nomic-ai/modernbert-embed-base` |
| Dimensions | 768 |
| Context Length | 8192 tokens |
| License | Apache 2.0 |

### Image Embeddings: SigLIP

| Property | Value |
|----------|-------|
| Model | `google/siglip-so400m-patch14-384` |
| Dimensions | 384 |
| Image Size | 384x384 |
| License | Apache 2.0 |

---

## Docker Setup

### Location

```
docker/
├── docker-compose.yml
├── up.sh
├── down.sh
└── status.sh
```

### Start Server

```bash
# Start everything (includes Infinity)
docker/up.sh

# Or start just Infinity
docker/up.sh infinity
```

### Stop Server

```bash
docker/down.sh
```

### Configuration

```yaml
# docker/docker-compose.yml

services:
  parallax-infinity:
    image: michaelf34/infinity:latest
    container_name: parallax-infinity
    ports:
      - "7997:7997"
    volumes:
      - ../.models/infinity:/app/.cache
    environment:
      - INFINITY_MODEL_ID=nomic-ai/modernbert-embed-base;google/siglip-so400m-patch14-384
      - INFINITY_PORT=7997
      - INFINITY_ENGINE=torch
      - INFINITY_BATCH_SIZE=32
      - INFINITY_DEVICE=cuda
```

---

## API Usage

### Text Embeddings

```python
import requests

INFINITY_HOST = "http://localhost:7997"
TEXT_MODEL = "nomic-ai/modernbert-embed-base"

# Single text
response = requests.post(
    f"{INFINITY_HOST}/v1/embeddings",
    json={
        "model": TEXT_MODEL,
        "input": "search_query: Why is the Earth flat?",
    },
)
embedding = response.json()["data"][0]["embedding"]
print(f"Dimension: {len(embedding)}")  # 768

# Batch texts
texts = [
    "search_document: Water always finds its level.",
    "search_document: The horizon appears flat from any height.",
]
response = requests.post(
    f"{INFINITY_HOST}/v1/embeddings",
    json={"model": TEXT_MODEL, "input": texts},
)
embeddings = [d["embedding"] for d in response.json()["data"]]
```

### Required Prefixes

**IMPORTANT:** ModernBERT requires prefixes for optimal performance:

```python
# For search queries
query = "search_query: Why is the earth flat?"

# For documents to be indexed
document = "search_document: Water always finds its level. Period."
```

### Image Embeddings

```python
import base64
import requests

IMAGE_MODEL = "google/siglip-so400m-patch14-384"

# Load image
with open("image.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

# Generate image embedding
response = requests.post(
    f"{INFINITY_HOST}/v1/embeddings",
    json={
        "model": IMAGE_MODEL,
        "input": [image_b64],
    },
)
image_embedding = response.json()["data"][0]["embedding"]
print(f"Dimension: {len(image_embedding)}")  # 384
```

### Text-Image Similarity

```python
import math

# Text embedding (use same model for comparable space)
text_response = requests.post(
    f"{INFINITY_HOST}/v1/embeddings",
    json={
        "model": IMAGE_MODEL,
        "input": ["a photo of cats"],
    },
)
text_emb = text_response.json()["data"][0]["embedding"]

# Image embedding
img_response = requests.post(
    f"{INFINITY_HOST}/v1/embeddings",
    json={"model": IMAGE_MODEL, "input": [image_b64]},
)
img_emb = img_response.json()["data"][0]["embedding"]

# Cosine similarity
dot_product = sum(a * b for a, b in zip(text_emb, img_emb))
norm_text = math.sqrt(sum(a * a for a in text_emb))
norm_img = math.sqrt(sum(b * b for b in img_emb))
similarity = dot_product / (norm_text * norm_img)
print(f"Similarity: {similarity:.4f}")
```

### cURL Examples

```bash
# Text embedding
curl http://localhost:7997/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-ai/modernbert-embed-base", "input": "Hello world"}'

# List models
curl http://localhost:7997/v1/models

# Health check
curl http://localhost:7997/health
```

---

## OpenViking Integration

### Configuration

```json
// ~/.openviking/ov.conf
{
  "embedding": {
    "dense": {
      "api_base": "http://localhost:7997/v1",
      "api_key": "dummy",
      "provider": "openai",
      "dimension": 768,
      "model": "nomic-ai/modernbert-embed-base"
    }
  },
  "vlm": {
    "api_base": "http://localhost:11433/v1",
    "provider": "ollama",
    "model": "granite3.3:2b"
  }
}
```

### Usage with OpenViking

```python
from openviking import SyncOpenViking

ov = SyncOpenViking(path="./memory/viking")

# OpenViking will use Infinity for embeddings
# when configured in ov.conf
results = ov.find(
    query="Why is the Earth flat?",
    target_uri="viking://resources/knowledge/flat-earth/",
    top_k=5
)
```

---

## Performance

### Throughput

| Model | Batch Size | GPU Speed | CPU Speed |
|-------|------------|-----------|-----------|
| modernbert-embed | 32 | ~800 docs/s | ~100 docs/s |
| modernbert-embed | 64 | ~1200 docs/s | N/A |
| siglip | 16 | ~200 images/s | ~30 images/s |

### Latency

| Model | Single Request | Batch (32) |
|-------|----------------|------------|
| modernbert-embed | ~5ms | ~40ms |
| siglip | ~20ms | ~150ms |

### Memory

| Model | VRAM | RAM (CPU) |
|-------|------|-----------|
| modernbert-embed | ~1GB | ~2GB |
| siglip | ~1.5GB | ~2.5GB |
| Both models | ~2GB | ~4GB |

---

## Testing

### Run Test Script

```bash
cd investigations/embeddings
python infinity_test.py
```

### Test Output

```
=== Infinity Embedding Server Test ===

--- Available Models ---
  - nomic-ai/modernbert-embed-base
  - google/siglip-so400m-patch14-384

--- Text Embedding Test ---
Model: nomic-ai/modernbert-embed-base
Texts: 3
Embedding dimension: 768
Latency: 12.34ms

--- Image Embedding Test ---
Model: google/siglip-so400m-patch14-384
Embedding dimension: 384
Latency: 45.67ms

--- Text-Image Similarity Test ---
Text: 'a photo of cats'
Image: cats on pink blanket
Similarity: 0.8523

=== All tests passed! ===
```

---

## Monitoring

See [plans/monitor.md](monitor.md) for Infinity metrics integration.

### Metrics Endpoint

```bash
curl http://localhost:7997/metrics
```

### Key Metrics

| Metric | Description |
|--------|-------------|
| `infinity_requests_total` | Total embedding requests |
| `infinity_latency_seconds` | Request latency |
| `infinity_batch_size` | Current batch size |
| `infinity_queue_depth` | Request queue depth |

---

## Use Cases

### Text Search (Viking Knowledge Base)

```python
# Index documents
for doc in documents:
    embedding = get_text_embedding(doc.content)
    ov.store_embedding(doc.uri, embedding)

# Search
query_embedding = get_text_embedding(f"search_query: {user_query}")
results = ov.find(query_embedding=query_embedding)
```

### Image Search (Vision Capabilities)

```python
# Index images with descriptions
for image in images:
    image_emb = get_image_embedding(image.data)
    text_emb = get_text_embedding(image.description)
    # Store both for hybrid search

# Search by text
query_emb = get_text_embedding("cats on a couch")
similar_images = find_similar(query_emb, image_embeddings)

# Search by image
query_emb = get_image_embedding(user_image)
similar_images = find_similar(query_emb, image_embeddings)
```

---

## Related Files

- [plans/memory.md](memory.md) - OpenViking configuration
- [plans/monitor.md](monitor.md) - Infinity metrics
- [plans/docker.md](docker.md) - Container architecture
- [docker/](../docker/) - Docker setup
- [investigations/embeddings/infinity_test.py](../investigations/embeddings/infinity_test.py) - Test script

---

## References

- [Infinity GitHub](https://github.com/michaelfeil/infinity)
- [Infinity Docs](https://michaelfeil.github.io/infinity/)
- [ModernBERT Model](https://huggingface.co/nomic-ai/modernbert-embed-base)
- [SigLIP Model](https://huggingface.co/google/siglip-so400m-patch14-384)
