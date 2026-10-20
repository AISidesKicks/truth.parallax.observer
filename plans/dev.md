# Development Guide

> Setup and workflow for parallax.observer development

## Conda Environment

**Always use the `parallax.observer` conda environment for this project.**

### Setup

```bash
# Create environment (already done)
conda create -n parallax.observer python=3.12 -y

# Activate environment
conda activate parallax.observer

# Install dependencies
pip install torch transformers accelerate sentence-transformers requests docling
```

### Activation

```bash
# Always activate before working
conda activate parallax.observer
```

### Installed Packages

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.12 | Runtime |
| PyTorch | 2.9.1+cu128 | Deep learning |
| Transformers | 4.57.1 | HuggingFace models |
| Sentence Transformers | 5.2.3 | Embeddings (ModernBERT) |
| Requests | latest | HTTP client for Ollama API |
| CUDA | 12.8 | GPU acceleration |

### Verification

```bash
# Verify environment is active
conda info --envs

# Should show * next to parallax.observer

# Test Ollama connection
curl http://localhost:11433/api/tags
```

---

## Ollama Development

### Start Ollama Server

```bash
# Start everything (includes Ollama)
docker/up.sh

# Or start just Ollama
docker/up.sh ollama
```

### Docker Commands

```bash
# View logs
docker logs -f parallax-ollama

# Stop container
docker stop parallax-ollama

# Shell into container
docker exec -it parallax-ollama bash

# Pull additional model
docker exec parallax-ollama ollama pull <model>
```

---

## App Development

### Start App Container

```bash
# Production mode (default)
docker/up.sh

# Development mode (hot reload)
docker/up.sh dev

# Stop all
docker/down.sh
```

### Docker Commands

```bash
# View app logs
docker logs -f parallax-app

# Shell into app container
docker exec -it parallax-app bash
```

### Environment Variables

```bash
# Ollama host
OLLAMA_HOST=http://localhost:11433

# Embeddings
EMBEDDING_MODEL=nomic-ai/modernbert-embed-base
EMBEDDING_DIMENSION=768
```

---

## Development Scripts

### Run Tests

```bash
conda activate parallax.observer
python -m pytest tests/
```

### Start Development Server

```bash
conda activate parallax.observer
./dev.sh
```

### Run Benchmark

```bash
cd investigations/ollama
python benchmark.py
```

### Test Vision Model

```bash
cd investigations/ollama
python test_vlm.py
```

---

## Model Access

### Granite Models (Open)

No authentication required:

- `granite3.3:2b` ✅
- `granite4:tiny-h` ✅
- `granite4:micro-h` ✅

### Qwen3-VL (Open)

No authentication required:

- `qwen3-vl:2b` ✅

### Nomic Embeddings (Open)

No authentication required:

- `nomic-ai/modernbert-embed-base` ✅

---

## IDE Setup

### VS Code

Select interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter" → `parallax.observer`

### PyCharm

Settings → Project → Python Interpreter → Add Conda Environment → `parallax.observer`

---

## Troubleshooting

### CUDA Not Detected

```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Should print: True
```

### Wrong Environment

```bash
# Check current env
echo $CONDA_DEFAULT_ENV

# Should be: parallax.observer
```

### Ollama Not Running

```bash
# Check container
docker ps | grep ollama

# Start if not running
docker/up.sh
```

### Package Conflicts

```bash
# Reinstall clean
conda deactivate
conda env remove -n parallax.observer
conda create -n parallax.observer python=3.12 -y
conda activate parallax.observer
pip install torch transformers accelerate sentence-transformers requests
```

### Docker GPU Access

```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Should show GPU info
```

---

## Related Files

- [plans/models.md](models.md) - Model documentation
- [plans/embeddings.md](embeddings.md) - Embedding setup
- [docker/](../docker/) - Docker configuration
- [investigations/ollama/](../investigations/ollama/) - Benchmark scripts
