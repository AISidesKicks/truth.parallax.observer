# Ollama Model Benchmark

Tests GGUF models via Ollama API for parallax.observer.

## Prerequisites

### Start Ollama Server

```bash
cd infra/aiserve/ollama
./up.sh
```

This starts the container and pulls all models.

## Models Tested

| Model | Ollama Tag | Size | Throughput | Notes |
|-------|------------|------|------------|-------|
| Granite-3.3-2B | `granite3.3:2b` | 1.5 GB | 154.7 tok/s | **Thinking mode** for reasoning |
| Granite-4.0-Tiny-H | `granite4:tiny-h` | 4.0 GB | 124.8 tok/s | MoE, 1B active, 128K context |
| Granite-4.0-Micro-H | `granite4:micro-h` | 2.0 GB | 107.6 tok/s | Hybrid mamba-2 |
| Qwen3-VL-2B | `qwen3-vl:2b` | 1.9 GB | ~40 tok/s | **Vision-language** for images |

### Thinking Mode (Granite 3.3)

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

### Vision Model (Qwen3-VL)

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

## Run Benchmark

```bash
cd investigations/ollama
python benchmark.py
```

## Configuration

The benchmark uses:
- **20 requests** per model
- **128 max tokens** per request
- **Temperature: 0.7**
- **Context window: 4096**

Ollama server settings:
- **Flash Attention**: Enabled (`OLLAMA_FLASH_ATTENTION=1`)
- **KV Cache**: 8-bit (`OLLAMA_KV_CACHE_TYPE=q8_0`)
- **Context Length**: 128K (`OLLAMA_CONTEXT_LENGTH=128000`)

## Metrics Collected

- **Load time** - seconds to load model into memory
- **Throughput** - tokens per second
- **Latency** - milliseconds per request
- **Aggregates** - avg tokens/sec, avg latency, total tokens

## Output

Results saved to `../benchmark_ollama_results.json`.

## Notes

- Ollama handles GPU memory management automatically
- Flash attention enabled via environment variable
- Models are automatically downloaded on first use
- Use `ollama rm <model>` to delete a model
- Use `keep_alive: 0` to unload model from GPU

## Related

- [plans/models.md](../../plans/models.md) - Model documentation
- [Ollama Library](https://ollama.com/library) - Available models
