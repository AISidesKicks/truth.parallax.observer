# Observability: Phoenix + OpenTelemetry

> LLM tracing and debugging with Arize Phoenix and OpenTelemetry

## Overview

parallax.observer uses **Arize Phoenix** for LLM observability with **OpenTelemetry** instrumentation. Phoenix is included in the default Docker setup.

| Component | Purpose | Port |
|-----------|---------|------|
| Phoenix UI | Trace visualization, debugging | 6006 |
| OTLP gRPC | OpenTelemetry receiver | 4317 |
| OTLP HTTP | OpenTelemetry receiver | 4318 |

---

## Phoenix Container

### Start/Stop

```bash
# Start everything (includes Phoenix)
docker/up.sh

# Start development mode (includes Phoenix)
docker/up.sh dev

# Stop all
docker/down.sh
```

### Access

- **UI**: http://localhost:6006
- **OTLP gRPC**: localhost:4317
- **OTLP HTTP**: localhost:4318

---

## OpenTelemetry Setup

### Dependencies

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation-requests
```

Or add to `requirements.txt`:

```
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp>=1.20.0
opentelemetry-instrumentation-requests>=0.41b0
```

### Configuration

```python
# src/observability/config.py

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def setup_telemetry(service_name: str = "parallax.observer"):
    """Initialize OpenTelemetry tracing."""
    
    phoenix_enabled = os.getenv("PHOENIX_ENABLED", "false").lower() == "true"
    
    if not phoenix_enabled:
        return None
    
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    
    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint=endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
```

### Environment Variables

```bash
# .env
PHOENIX_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=parallax.observer
```

---

## Instrumentation

### LLM Call Tracing

```python
# src/observability/llm_tracing.py

import os
from opentelemetry import trace
from functools import wraps

tracer = trace.get_tracer("parallax.observer.llm")

def trace_llm_call(model: str):
    """Decorator to trace LLM API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if os.getenv("PHOENIX_ENABLED") != "true":
                return func(*args, **kwargs)
            
            with tracer.start_as_current_span(f"llm.call.{model}") as span:
                span.set_attribute("llm.model", model)
                span.set_attribute("llm.provider", "ollama")
                
                # Extract prompt
                prompt = kwargs.get("prompt", args[0] if args else "")
                span.set_attribute("llm.prompt", prompt[:500])
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Track tokens
                    if isinstance(result, dict):
                        span.set_attribute("llm.tokens", result.get("eval_count", 0))
                        span.set_attribute("llm.tokens_per_sec", 
                            result.get("eval_count", 0) / max(result.get("total_duration", 1) / 1e9, 0.001))
                    
                    span.set_attribute("llm.status", "success")
                    return result
                    
                except Exception as e:
                    span.set_attribute("llm.status", "error")
                    span.set_attribute("llm.error", str(e))
                    raise
        
        return wrapper
    return decorator
```

### Usage with Ollama

```python
# src/llm/client.py

import requests
from src.observability.llm_tracing import trace_llm_call

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11433"):
        self.host = host
    
    @trace_llm_call(model="ollama")
    def generate(self, model: str, prompt: str, **options) -> dict:
        """Generate response from Ollama."""
        response = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options,
            },
            timeout=120,
        )
        return response.json()
```

### Embedding Tracing

```python
# src/observability/embedding_tracing.py

import os
from opentelemetry import trace

tracer = trace.get_tracer("parallax.observer.embeddings")

def trace_embedding(func):
    """Decorator to trace embedding generation."""
    def wrapper(texts, **kwargs):
        if os.getenv("PHOENIX_ENABLED") != "true":
            return func(texts, **kwargs)
        
        with tracer.start_as_current_span("embedding.generate") as span:
            span.set_attribute("embedding.model", "modernbert-embed-base")
            span.set_attribute("embedding.text_count", len(texts) if isinstance(texts, list) else 1)
            
            result = func(texts, **kwargs)
            
            if hasattr(result, 'shape'):
                span.set_attribute("embedding.dimensions", result.shape[-1])
            
            return result
    
    return wrapper
```

### API Request Tracing

```python
# src/observability/api_tracing.py

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def instrument_app(app):
    """Instrument FastAPI app with OpenTelemetry."""
    if os.getenv("PHOENIX_ENABLED") == "true":
        FastAPIInstrumentor.instrument_app(app)
```

---

## Metrics

### Token Counter

```python
# src/observability/metrics.py

from opentelemetry import metrics

meter = metrics.get_meter("parallax.observer")

token_counter = meter.create_counter(
    "llm.tokens.total",
    description="Total LLM tokens generated",
)

latency_histogram = meter.create_histogram(
    "llm.latency",
    description="LLM request latency in milliseconds",
)

error_counter = meter.create_counter(
    "llm.errors.total",
    description="Total LLM errors",
)

def record_llm_metrics(model: str, tokens: int, latency_ms: float, error: bool = False):
    """Record LLM metrics."""
    token_counter.add(tokens, {"model": model})
    latency_histogram.record(latency_ms, {"model": model})
    if error:
        error_counter.add(1, {"model": model})
```

---

## Structured Logging

```python
# src/observability/logging.py

import logging
import json
from opentelemetry import trace

class StructuredFormatter(logging.Formatter):
    """JSON structured logging with trace context."""
    
    def format(self, record):
        span = trace.get_current_span()
        span_context = span.get_span_context()
        
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": f"{span_context.trace_id:032x}" if span_context.is_valid else None,
            "span_id": f"{span_context.span_id:016x}" if span_context.is_valid else None,
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging():
    """Configure structured logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
```

---

## Phoenix UI Guide

### Viewing Traces

1. Open http://localhost:6006
2. Navigate to **Traces** tab
3. Filter by:
   - Service: `parallax.observer`
   - Operation: `llm.call.*`, `embedding.generate`
   - Time range

### Analyzing LLM Performance

- **Latency Distribution**: See p50, p95, p99 latencies
- **Token Throughput**: Tokens per second per model
- **Error Rates**: Failed requests by model
- **Prompt Analysis**: View actual prompts and responses

### Spans

| Span Name | Attributes |
|-----------|------------|
| `llm.call.{model}` | model, prompt, tokens, tokens_per_sec, status |
| `embedding.generate` | model, text_count, dimensions |
| `api.request.{endpoint}` | method, path, status_code |

---

## Docker Configuration

Phoenix runs as a separate container in the unified Docker setup:

```yaml
# docker/docker-compose.yml

services:
  parallax-phoenix:
    image: arizephoenix/phoenix:latest
    container_name: parallax-phoenix
    ports:
      - "6006:6006"  # UI
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
    volumes:
      - phoenix_data:/root/.phoenix
    environment:
      - PHOENIX_HOST=0.0.0.0
      - PHOENIX_PORT=6006
    profiles:
      - phoenix
```

---

## Startup Order

```bash
# 1. Start everything (includes Phoenix)
docker/up.sh

# 2. Enable Phoenix in app
export PHOENIX_ENABLED=true
```

---

## Troubleshooting

### Phoenix Not Receiving Traces

```bash
# Check Phoenix is running
docker ps | grep phoenix

# Check OTLP endpoint
curl http://localhost:4318/v1/traces

# Verify environment variable
echo $PHOENIX_ENABLED
```

### High Memory Usage

Phoenix stores traces in memory. For long sessions:

```bash
# Clear Phoenix data
docker volume rm phoenix_data
```

### Missing Traces

- Ensure `PHOENIX_ENABLED=true` is set before starting the app
- Check OTLP endpoint matches Phoenix container
- Verify OpenTelemetry SDK is installed

---

## Related Files

- [plans/docker.md](docker.md) - Docker architecture
- [docker/](../docker/) - Docker configuration
- [Arize Phoenix Docs](https://docs.arize.com/phoenix)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
