# Docker Architecture

> Unified Docker setup for parallax.observer

## Overview

parallax.observer runs as a set of Docker containers with a unified network. All Docker configuration is consolidated in the `docker/` directory.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         parallax-lab Network                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ parallax-ollama │  │parallax-infinity│  │ parallax-phoenix│            │
│  │                 │  │                 │  │                 │            │
│  │ Port: 11433     │  │ Port: 7997      │  │ Port: 6006      │            │
│  │                 │  │                 │  │ Port: 4317/4318 │            │
│  │ granite3.3:2b   │  │ modernbert-embed│  │ Phoenix UI      │            │
│  │ granite4:tiny-h │  │ siglip (images) │  │ OTLP Receiver   │            │
│  │ granite4:micro-h│  │                 │  │                 │            │
│  │ qwen3-vl:2b     │  │                 │  │                 │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│           │                    │                    │                      │
│           │                    │                    │                      │
│           ▼                    ▼                    ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       parallax-app / parallax-dev                   │   │
│  │  FastAPI App | OpenViking | Ollama client | Infinity client        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
docker/
├── docker-compose.yml    # Unified compose with profiles
├── Dockerfile.app        # App container image
├── up.sh                 # Unified startup script
├── down.sh               # Stop all containers
├── status.sh             # Container status check
├── tests.sh              # Test script
└── README.md             # Quick reference
```

---

## Quick Start

```bash
# Default (production with observability)
docker/up.sh

# Development (hot reload)
docker/up.sh dev

# Individual services
docker/up.sh ollama
docker/up.sh ollama infinity

# Run tests
docker/tests.sh

# Check status
docker/status.sh

# Stop all
docker/down.sh
```

---

## Services

| Container | Image | Profile | Ports | GPU | Purpose |
|-----------|-------|---------|-------|-----|---------|
| `parallax-ollama` | `ollama/ollama:latest` | ollama | 11433:11434 | ✅ | LLM/VLM inference |
| `parallax-infinity` | `michaelf34/infinity:latest` | infinity | 7997:7997 | ✅ | Text & image embeddings |
| `parallax-phoenix` | `arizephoenix/phoenix:latest` | phoenix | 6006, 4317, 4318 | ❌ | Observability (tracing) |
| `parallax-app` | custom | app | 8668:8668 | ❌ | Production application |
| `parallax-dev` | custom | dev | 8668:8668 | ✅ | Development with GPU monitoring |

---

## Startup Modes

### Default (No Arguments)

```bash
docker/up.sh
```

Starts: ollama + infinity + phoenix + app

### Development

```bash
docker/up.sh dev
```

Starts: ollama + infinity + phoenix + dev (hot reload, debug logging)

### Individual Services

```bash
docker/up.sh ollama       # Just Ollama
docker/up.sh infinity     # Just Infinity
docker/up.sh phoenix      # Just Phoenix
docker/up.sh ollama infinity app  # Custom combination
```

---

## Network

All containers share the **parallax-lab** network for inter-container communication.

```bash
# Create network (automatic via up.sh)
docker network create parallax-lab

# Verify network
docker network ls | grep parallax
```

---

## Volumes

| Volume | Container | Purpose |
|--------|-----------|---------|
| `.models/ollama` | ollama | GGUF models (persisted) |
| `.models/infinity` | infinity | Embedding models (persisted) |
| `memory/viking` | app, dev | OpenViking memory storage |
| `facts` | app, dev | Knowledge base files |
| `.logs` | app, dev | Application logs |
| `phoenix_data` | phoenix | Phoenix trace storage |

---

## Startup Order

Services start with proper dependency ordering:

1. **parallax-ollama** (waits for health check)
2. **parallax-infinity** (waits for startup)
3. **parallax-phoenix** (independent)
4. **parallax-app** / **parallax-dev** (waits for ollama + infinity)

```bash
# Just run locally without Docker
./dev.sh
```

---

## Common Commands

### Container Management

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop all parallax containers
docker/down.sh

# Stop specific container
docker stop parallax-ollama parallax-app
```

### Logs

```bash
# Ollama logs
docker logs -f parallax-ollama

# App logs
docker logs -f parallax-app

# Phoenix logs
docker logs -f parallax-phoenix

# Infinity logs
docker logs -f parallax-infinity
```

### Shell Access

```bash
# Shell into Ollama
docker exec -it parallax-ollama bash

# Shell into app
docker exec -it parallax-app bash

# Pull new model in Ollama
docker exec parallax-ollama ollama pull <model>
```

---

## GPU Configuration

### GPU-Enabled Containers

Three containers have GPU access via NVIDIA runtime:

| Container | GPU Access | Purpose |
|-----------|------------|---------|
| `parallax-ollama` | ✅ Full | LLM/VLM inference on GPU |
| `parallax-infinity` | ✅ Full | Embedding computation on GPU |
| `parallax-dev` | ✅ Full | GPU monitoring with `nvidia-ml-py` |
| `parallax-app` | ❌ No | Production app (CPU only) |
| `parallax-phoenix` | ❌ No | Observability (CPU only) |

### GPU Configuration in docker-compose.yml

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### GPU Environment Variables (dev container)

```yaml
environment:
  - NVIDIA_VISIBLE_DEVICES=all
  - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### GPU Monitoring in Dev Container

The `parallax-dev` container can use `nvidia-ml-py` for GPU monitoring:

```python
import nvidia_smi

nvidia_smi.nvmlInit()
handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)

# Get GPU stats
mem = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
util = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
temp = nvidia_smi.nvmlDeviceGetTemperature(handle, nvidia_smi.NVML_TEMPERATURE_GPU)

print(f"GPU Temp: {temp}°C")
print(f"VRAM: {mem.used // 1024**3}GB / {mem.total // 1024**3}GB")
print(f"GPU Util: {util.gpu}%")
```

### Prerequisites

**Host System:**
1. NVIDIA GPU drivers installed
2. NVIDIA Container Toolkit installed

```bash
# Install NVIDIA Container Toolkit (Ubuntu/Debian)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### GPU Debugging

```bash
# Check GPU access in container
docker exec parallax-ollama nvidia-smi

# Check Ollama GPU usage
docker exec parallax-ollama ollama ps
```

---

## Environment Variables

### Ollama

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_FLASH_ATTENTION` | 1 | Enable flash attention |
| `OLLAMA_KV_CACHE_TYPE` | q8_0 | 8-bit KV cache |
| `OLLAMA_CONTEXT_LENGTH` | 128000 | Max context length |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | http://parallax-ollama:11434 | Ollama endpoint |
| `EMBEDDING_MODEL` | nomic-ai/modernbert-embed-base | Embedding model |
| `EMBEDDING_DIMENSION` | 768 | Embedding dimensions |
| `LOG_LEVEL` | INFO | Logging level |
| `DEBUG` | false | Debug mode |
| `PHOENIX_ENABLED` | false | Enable OpenTelemetry |

### Phoenix

| Variable | Default | Description |
|----------|---------|-------------|
| `PHOENIX_HOST` | 0.0.0.0 | Bind address |
| `PHOENIX_PORT` | 6006 | UI port |

---

## Architecture Details

### Ollama Container

```yaml
services:
  parallax-ollama:
    image: ollama/ollama:latest
    ports:
      - "11433:11434"
    volumes:
      - ../.models/ollama:/root/.ollama
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

### Application Container

```yaml
services:
  parallax-app:
    build:
      context: ..
      dockerfile: docker/Dockerfile.app
    ports:
      - "8668:8668"
    volumes:
      - ../memory/viking:/app/viking_data
      - ../facts:/app/facts
      - ../.logs:/app/logs
    environment:
      - OLLAMA_HOST=http://parallax-ollama:11434
```

### Development Container (with GPU)

```yaml
services:
  parallax-dev:
    build:
      context: ..
      dockerfile: docker/Dockerfile.app
    ports:
      - "8668:8668"
    volumes:
      - ../src:/app/src
      - ../models:/app/models
      - ../.env:/app/.env:ro
    environment:
      - OLLAMA_HOST=http://parallax-ollama:11434
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - DEBUG=true
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Phoenix Container

```yaml
services:
  parallax-phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
      - "4317:4317"
      - "4318:4318"
```

---

## Quick Reference

### Start Everything

```bash
# Production (default)
docker/up.sh

# Development
docker/up.sh dev
```

### Stop Everything

```bash
docker/down.sh
```

### Check Status

```bash
docker/status.sh
```

### Full Reset

```bash
# Stop and remove all
docker/down.sh
docker rm parallax-ollama parallax-app parallax-dev parallax-phoenix parallax-infinity 2>/dev/null || true

# Remove volumes (optional - clears data)
docker volume rm phoenix_data 2>/dev/null || true

# Restart
docker/up.sh
```

---

## Related Files

- [plans/observability.md](observability.md) - Phoenix + OpenTelemetry
- [plans/models.md](models.md) - Model configuration
- [plans/dev.md](dev.md) - Development workflow
- [docker/docker-compose.yml](../docker/docker-compose.yml) - Main compose file
