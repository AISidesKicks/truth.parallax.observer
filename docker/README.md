# Docker - parallax.observer

Unified Docker setup for all containers. Everything runs locally: one
llama.cpp server that hosts both models, and the OpenViking context server.

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
| `prlx-llm` | 11433 | llama.cpp router, chat and embeddings | Yes |
| `prlx-embed` | 7997 | Standalone embedding server, optional | Yes |
| `prlx-viking` | 1933 | OpenViking context server | No |
| `prlx-phoenix` | 6006, 4317, 4318 | Observability | No |
| `prlx-app` | 8668 | Production application | No |
| `prlx-dev` | 8668 | Development (hot reload) | No |

## One server, two models

llama.cpp v0.7.0 can run in router mode. The server starts without a model
and loads the right one per request, based on the `model` field in the body.
`config/llama-models.ini` defines both presets:

```ini
[granite-4.0-h-tiny]
model = /models/granite-4.0-h-tiny-Q4_K_M.gguf
...

[embeddinggemma-2]
model = /models/embeddinggemma-2-Q8_0.gguf
embeddings = true
pooling = last
...
```

So the chat call and the embedding call both go to port 11433, they just
name a different model. That is one CUDA context instead of two, which
matters on a 12 GB card that is shared with other projects.

If you prefer the encoder in its own container, start the `embed` profile and
point `EMBEDDING_API_BASE` at it:

```bash
./up.sh llm embed viking phoenix app
# then in .env
# EMBEDDING_API_BASE=http://prlx-embed:8080/v1
```

## Startup Modes

### Default (No Arguments)

```bash
./up.sh
```

Starts: llm + viking + phoenix + app

### Development

```bash
./up.sh dev
```

Starts: llm + viking + phoenix + dev (hot reload, debug logging)

### Individual Services

```bash
./up.sh llm        # Just the model server
./up.sh embed      # Just the standalone embedding server
./up.sh viking     # Just the OpenViking server
./up.sh phoenix    # Just Phoenix
./up.sh llm embed viking app  # Custom combination
```

## Endpoints

| Service | URL |
|---------|-----|
| Chat and embeddings | http://localhost:11433/v1 |
| Standalone embeddings | http://localhost:7997/v1 |
| OpenViking | http://localhost:1933 |
| Phoenix UI | http://localhost:6006 |
| App | http://localhost:8668 |

## Models

Both models run in the same image, `ghcr.io/ggml-org/llama.cpp:server-cuda13`.

| Role | Model | Repo | Size | Quant |
|------|-------|------|------|-------|
| Chat | granite-4.0-h-tiny | `ibm-granite/granite-4.0-h-tiny-GGUF` | 4231 MB | Q4_K_M |
| Embeddings | embeddinggemma-2 | `ggml-org/embeddinggemma-2-GGUF` | 310 MB | Q8_0 |

EmbeddingGemma 2 is multimodal and outputs 768 dimensions with MRL
truncation down to 128.

Both are downloaded by `./fetch-models.sh` into `.models/llama`.

## GPU budget

The chat model takes roughly 4.5 GB of VRAM, the embedding model roughly
0.6 GB. Check what is left before starting them:

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

## Volumes

| Host Path | Container | Purpose |
|-----------|-----------|---------|
| `.models/llama` | /models | GGUF models (read-only) |
| `config/llama-models.ini` | /app/models.ini | Model presets (read-only) |
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
# llama.cpp
LLM_PORT=11433
LLM_MODEL_ALIAS=granite-4.0-h-tiny
LLM_API_BASE=http://localhost:11433/v1
EMBEDDING_API_BASE=http://localhost:11433/v1
EMBED_MODEL_ALIAS=embeddinggemma-2

# OpenViking
VIKING_PORT=1933
VIKING_WORKSPACE=/app/viking_data
VIKING_EMBEDDING_BASE=http://prlx-llm:8080/v1
VIKING_VLM_BASE=http://prlx-llm:8080/v1

# Embeddings (app side)
EMBEDDING_MODEL=embeddinggemma-2
EMBEDDING_DIMENSION=768

# Phoenix
PHOENIX_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://prlx-phoenix:4317
```

`config/openviking.conf` is rendered by the OpenViking server itself: every
`${VAR}` placeholder is expanded from the environment at load time. The
entrypoint refuses to start if a placeholder is left unresolved.

## Startup Order

Services start with proper dependency ordering:

1. **prlx-llm** (waits for health check)
2. **prlx-viking** (waits for llm, optional)
3. **prlx-phoenix** (independent)
4. **prlx-app** / **prlx-dev** (waits for viking + llm)
