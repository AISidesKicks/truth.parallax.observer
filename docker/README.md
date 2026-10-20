# Docker - parallax.observer

Unified Docker setup for all containers. Everything runs locally: two
llama.cpp servers (chat + embeddings) and the OpenViking context server.

Every container, volume and network carries the `prlx-` prefix, so nothing
here collides with the other projects sharing this Docker host.

## Quick Start

```bash
# Download the GGUF models first (they live on the host, not in the image)
./fetch-models.sh

# Default (production with observability)
./up.sh

# Development (hot reload)
./up.sh dev

# Individual services
./up.sh llm
./up.sh embed viking

# Run tests
./tests.sh

# Check status
./status.sh

# Stop all
./down.sh
```

## Services

| Service | Port | Purpose | GPU |
|---------|------|---------|-----|
| `prlx-llm` | 11433 | Chat / reasoning via llama.cpp | Yes |
| `prlx-embed` | 7997 | Text embeddings via llama.cpp | Yes |
| `prlx-viking` | 1933 | OpenViking context server | No |
| `prlx-phoenix` | 6006, 4317, 4318 | Observability | No |
| `prlx-app` | 8668 | Production application | No |
| `prlx-dev` | 8668 | Development (hot reload) | No |

## Startup Modes

### Default (No Arguments)

```bash
./up.sh
```

Starts: llm + embed + viking + phoenix + app

### Development

```bash
./up.sh dev
```

Starts: llm + embed + viking + phoenix + dev (hot reload, debug logging)

### Individual Services

```bash
./up.sh llm        # Just the chat server
./up.sh embed      # Just the embedding server
./up.sh viking     # Just the OpenViking server
./up.sh phoenix    # Just Phoenix
./up.sh llm embed viking app  # Custom combination
```

## Endpoints

| Service | URL |
|---------|-----|
| Chat (llama.cpp) | http://localhost:11433/v1 |
| Embeddings (llama.cpp) | http://localhost:7997/v1 |
| OpenViking | http://localhost:1933 |
| Phoenix UI | http://localhost:6006 |
| App | http://localhost:8668 |

## Models

Both servers run the same image, `ghcr.io/ggml-org/llama.cpp:server-cuda13`.
The chat server loads a text model, the embedding server loads an encoder.

### Chat model

| Model | Repo | Size (Q4_K_M) | Use Case |
|-------|------|---------------|----------|
| granite-4.0-h-tiny | `ibm-granite/granite-4.0-h-tiny-GGUF` | 4231 MB | Hybrid MoE, 128K ctx, thinking mode |

### Embedding model

| Model | Repo | Size (Q8_0) | Dimensions |
|-------|------|-------------|------------|
| embeddinggemma-2 | `ggml-org/embeddinggemma-2-GGUF` | 310 MB | 768 |

Both are downloaded by `./fetch-models.sh` into `.models/llama`.

## GPU budget

The chat model takes roughly 4.5 GB of VRAM, the embedding server roughly
0.6 GB. Check what is left before starting them:

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

## Volumes

| Host Path | Container | Purpose |
|-----------|-----------|---------|
| `.models/llama` | /models | GGUF models (read-only) |
| `memory/openviking` | /app/viking_data | OpenViking workspace |
| `facts/` | /app/facts | Wisdom corpus (read-only) |
| `config/` | /app/config | Runtime configuration (read-only) |
| `.logs/app` | /app/logs | Application logs |

## Common Commands

```bash
# View logs
docker logs -f prlx-llm
docker logs -f prlx-viking
docker logs -f prlx-app

# Shell access
docker exec -it prlx-app bash

# OpenViking CLI
docker exec -it prlx-viking ov ls viking://resources

# GPU check
docker exec prlx-llm nvidia-smi
```

## Environment Variables

Defined in `.env` (see `.env.sample`):

```bash
# llama.cpp servers
LLM_PORT=11433
LLM_MODEL_FILE=granite-4.0-h-tiny-Q4_K_M.gguf
LLM_MODEL_ALIAS=granite-4.0-h-tiny
LLM_CTX_SIZE=32768
EMBED_PORT=7997
EMBED_MODEL_FILE=embeddinggemma-2-Q8_0.gguf
EMBED_MODEL_ALIAS=embeddinggemma-2

# OpenViking
VIKING_PORT=1933
VIKING_WORKSPACE=/app/viking_data
VIKING_EMBEDDING_BASE=http://prlx-embed:8080/v1
VIKING_VLM_BASE=http://prlx-llm:8080/v1

# Embeddings (app side)
EMBEDDING_MODEL=embeddinggemma-2
EMBEDDING_DIMENSION=768

# Phoenix
PHOENIX_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://prlx-phoenix:4317
```

`config/openviking.conf` is rendered by the OpenViking server itself: every
`${VAR}` placeholder is expanded from the environment at load time.

## Startup Order

Services start with proper dependency ordering:

1. **prlx-llm** and **prlx-embed** (wait for health check)
2. **prlx-viking** (waits for llm + embed, both optional)
3. **prlx-phoenix** (independent)
4. **prlx-app** / **prlx-dev** (waits for viking + llm)
