Next time proces this inspirations:

 https://markaicode.com/monitor-gpu-usage-ollama-performance-tracking/ 

# Monitoring: GPU, CUDA, and Performance

> Real-time GPU/CUDA monitoring integrated with Phoenix traces

## Overview

Monitor GPU performance during LLM inference, correlating hardware metrics with LLM call traces in Phoenix. This enables debugging of memory issues, performance bottlenecks, and resource utilization.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Monitoring Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │     App     │───►│   Phoenix   │───►│  Dashboard  │         │
│  │  (pynvml)   │    │  (traces)   │    │  (terminal) │         │
│  └──────┬──────┘    └──────┬──────┘    └─────────────┘         │
│         │                  │                                    │
│         ▼                  ▼                                    │
│    GPU Metrics        LLM Spans                                 │
│    ┌─────────┐       ┌──────────┐                              │
│    │ VRAM    │       │ tokens   │                              │
│    │ Util %  │       │ latency  │                              │
│    │ Temp    │       │ model    │                              │
│    │ Power   │       │ prompt   │                              │
│    └─────────┘       └──────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

### Required

```bash
pip install pynvml psutil rich
```

### Optional (for advanced dashboard)

```bash
pip install textual  # Full TUI dashboard
```

### requirements.txt

```
pynvml>=11.5.0
psutil>=5.9.0
rich>=13.0.0
```

---

## Metrics Collected

### GPU Metrics (pynvml)

| Metric | Description | Unit |
|--------|-------------|------|
| `gpu_utilization` | GPU compute utilization | % |
| `gpu_memory_used` | VRAM allocated | MB |
| `gpu_memory_free` | VRAM available | MB |
| `gpu_memory_total` | Total VRAM | MB |
| `gpu_temperature` | GPU temperature | °C |
| `gpu_power_draw` | Power consumption | W |
| `gpu_power_limit` | Max power limit | W |
| `gpu_fan_speed` | Fan speed | % |

### CUDA Metrics (torch.cuda)

| Metric | Description | Unit |
|--------|-------------|------|
| `cuda_memory_allocated` | PyTorch allocated memory | MB |
| `cuda_memory_reserved` | PyTorch reserved memory | MB |
| `cuda_memory_cached` | Cached memory | MB |
| `cuda_max_memory_allocated` | Peak allocated | MB |

### Ollama Metrics (API)

| Metric | Description | Unit |
|--------|-------------|------|
| `model_loaded` | Currently loaded model | string |
| `model_size` | Model memory footprint | MB |
| `tokens_generated` | Tokens in response | count |
| `tokens_per_second` | Generation speed | tok/s |
| `eval_duration` | Generation time | ms |
| `prompt_eval_duration` | Prompt processing | ms |

### Application Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `request_latency` | End-to-end latency | ms |
| `request_count` | Total requests | count |
| `error_count` | Failed requests | count |
| `active_requests` | Concurrent requests | count |

### Agentic Metrics

See [plans/agentic.md](agentic.md) for context management details.

| Metric | Description | Unit | Alert Threshold |
|--------|-------------|------|-----------------|
| `context_tokens` | Current context window size | count | > 12,000 |
| `compression_events` | Context compressions triggered | count | > 5/session |
| `viking_retrievals` | KB queries per turn | count | > 10 |
| `agent_latency_ms` | Per-agent response time | ms | > 2,000 |
| `tactic_success_rate` | Arguments user accepted | % | < 30% |
| `emotion_distribution` | Emotion state counts | dict | N/A |

**Context Token Tracking:**

```python
# Track context window usage
context_tokens = count_tokens([
    system_prompt,
    viking_l1_overview,
    conversation_summary,
    recent_turns,
    current_query,
])

# Alert if approaching limit
if context_tokens > 12000:
    trigger_compression()
```

### Infinity Metrics (Embeddings)

See [plans/embeddings.md](embeddings.md) for Infinity embedding server setup.

| Metric | Description | Unit | Alert Threshold |
|--------|-------------|------|-----------------|
| `infinity_requests_total` | Total embedding requests | count | N/A |
| `infinity_latency_ms` | Embedding generation latency | ms | > 100ms |
| `infinity_text_embeds` | Text embeddings generated | count | N/A |
| `infinity_image_embeds` | Image embeddings generated | count | N/A |
| `infinity_batch_size` | Current batch size | count | > 64 |
| `infinity_queue_depth` | Request queue depth | count | > 10 |

**Infinity Monitoring Implementation:**

```python
# src/monitoring/infinity.py

import requests
from dataclasses import dataclass
from typing import Optional

INFINITY_HOST = "http://localhost:7997"

@dataclass
class InfinityMetrics:
    requests_total: int
    latency_ms: float
    text_embeddings: int
    image_embeddings: int
    batch_size: int
    queue_depth: int

def get_infinity_metrics(host: str = INFINITY_HOST) -> Optional[InfinityMetrics]:
    """Get metrics from Infinity /metrics endpoint."""
    try:
        response = requests.get(f"{host}/metrics", timeout=5)
        # Parse Prometheus-style metrics
        metrics = {}
        for line in response.text.split("\n"):
            if line.startswith("infinity_"):
                parts = line.split()
                if len(parts) == 2:
                    metrics[parts[0]] = float(parts[1])
        
        return InfinityMetrics(
            requests_total=int(metrics.get("infinity_requests_total", 0)),
            latency_ms=metrics.get("infinity_latency_seconds", 0) * 1000,
            text_embeddings=int(metrics.get("infinity_text_embeddings_total", 0)),
            image_embeddings=int(metrics.get("infinity_image_embeddings_total", 0)),
            batch_size=int(metrics.get("infinity_batch_size", 0)),
            queue_depth=int(metrics.get("infinity_queue_depth", 0)),
        )
    except Exception as e:
        print(f"Failed to get Infinity metrics: {e}")
        return None

def check_infinity_health(host: str = INFINITY_HOST) -> bool:
    """Check if Infinity is healthy."""
    try:
        response = requests.get(f"{host}/health", timeout=5)
        return response.status_code == 200
    except:
        return False
```

**GUI Monitoring Bar Update:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ [GPU] RTX 3080 | Util: 87% | VRAM: 4.2/10GB | Temp: 72°C           │
│ [LLM] granite3.3:2b | 154 tok/s | [EMB] Infinity | 8ms/emb        │
│ [APP] Requests: 23 | Latency: 890ms | CTX: 8.2K/16K                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

### GPU Monitor Module

```python
# src/monitoring/gpu.py

import pynvml
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class GPUMetrics:
    """GPU metrics snapshot."""
    device_name: str
    utilization_gpu: float  # %
    utilization_memory: float  # %
    memory_used: int  # bytes
    memory_free: int  # bytes
    memory_total: int  # bytes
    temperature: int  # Celsius
    power_draw: int  # mW
    power_limit: int  # mW
    fan_speed: int  # %
    
    @property
    def memory_used_mb(self) -> float:
        return self.memory_used / (1024 ** 2)
    
    @property
    def memory_utilization_percent(self) -> float:
        return (self.memory_used / self.memory_total) * 100
    
    @property
    def power_utilization_percent(self) -> float:
        return (self.power_draw / self.power_limit) * 100 if self.power_limit > 0 else 0


class GPUMonitor:
    """NVIDIA GPU monitoring using pynvml."""
    
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._initialized = False
        self._handle = None
    
    def initialize(self):
        """Initialize NVML connection."""
        try:
            pynvml.nvmlInit()
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
            self._initialized = True
        except pynvml.NVMLError as e:
            raise RuntimeError(f"Failed to initialize NVML: {e}")
    
    def shutdown(self):
        """Shutdown NVML connection."""
        if self._initialized:
            pynvml.nvmlShutdown()
            self._initialized = False
    
    def get_metrics(self) -> Optional[GPUMetrics]:
        """Get current GPU metrics."""
        if not self._initialized:
            return None
        
        try:
            device_name = pynvml.nvmlDeviceGetName(self._handle)
            
            # Utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(self._handle)
            
            # Memory
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
            
            # Temperature
            temp = pynvml.nvmlDeviceGetTemperature(
                self._handle, pynvml.NVML_TEMPERATURE_GPU
            )
            
            # Power
            power_draw = pynvml.nvmlDeviceGetPowerUsage(self._handle)
            power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(self._handle)
            
            # Fan speed (may not be available on all GPUs)
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(self._handle)
            except pynvml.NVMLError:
                fan_speed = 0
            
            return GPUMetrics(
                device_name=device_name,
                utilization_gpu=util.gpu,
                utilization_memory=util.memory,
                memory_used=mem_info.used,
                memory_free=mem_info.free,
                memory_total=mem_info.total,
                temperature=temp,
                power_draw=power_draw,
                power_limit=power_limit,
                fan_speed=fan_speed,
            )
        except pynvml.NVMLError as e:
            print(f"GPU monitoring error: {e}")
            return None
    
    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# Global instance
_monitor: Optional[GPUMonitor] = None


def get_gpu_monitor() -> Optional[GPUMonitor]:
    """Get or create GPU monitor instance."""
    global _monitor
    
    if os.getenv("GPU_MONITORING", "false").lower() != "true":
        return None
    
    if _monitor is None:
        _monitor = GPUMonitor()
        _monitor.initialize()
    
    return _monitor
```

### CUDAMetrics Module

```python
# src/monitoring/cuda.py

import torch
from dataclasses import dataclass
from typing import Optional


@dataclass
class CUDAMetrics:
    """PyTorch CUDA memory metrics."""
    memory_allocated: int  # bytes
    memory_reserved: int  # bytes
    memory_cached: int  # bytes
    max_memory_allocated: int  # bytes
    
    @property
    def memory_allocated_mb(self) -> float:
        return self.memory_allocated / (1024 ** 2)
    
    @property
    def memory_reserved_mb(self) -> float:
        return self.memory_reserved / (1024 ** 2)


def get_cuda_metrics() -> Optional[CUDAMetrics]:
    """Get current CUDA memory metrics."""
    if not torch.cuda.is_available():
        return None
    
    return CUDAMetrics(
        memory_allocated=torch.cuda.memory_allocated(),
        memory_reserved=torch.cuda.memory_reserved(),
        memory_cached=torch.cuda.memory_reserved(),
        max_memory_allocated=torch.cuda.max_memory_allocated(),
    )


def reset_cuda_stats():
    """Reset CUDA peak memory tracking."""
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()
```

### Phoenix Integration

```python
# src/monitoring/telemetry.py

from opentelemetry import trace
from functools import wraps
from typing import Optional, Callable
import time

from .gpu import get_gpu_monitor
from .cuda import get_cuda_metrics


tracer = trace.get_tracer("parallax.observer.monitoring")


def get_gpu_attributes() -> dict:
    """Get GPU metrics as span attributes."""
    attrs = {}
    
    gpu_monitor = get_gpu_monitor()
    if gpu_monitor:
        metrics = gpu_monitor.get_metrics()
        if metrics:
            attrs.update({
                "gpu.utilization_percent": metrics.utilization_gpu,
                "gpu.memory_used_mb": metrics.memory_used_mb,
                "gpu.memory_utilization_percent": metrics.memory_utilization_percent,
                "gpu.temperature_c": metrics.temperature,
                "gpu.power_draw_w": metrics.power_draw / 1000,
                "gpu.power_utilization_percent": metrics.power_utilization_percent,
            })
    
    cuda_metrics = get_cuda_metrics()
    if cuda_metrics:
        attrs.update({
            "cuda.memory_allocated_mb": cuda_metrics.memory_allocated_mb,
            "cuda.memory_reserved_mb": cuda_metrics.memory_reserved_mb,
        })
    
    return attrs


def trace_llm_with_gpu(model: str):
    """Decorator to trace LLM calls with GPU metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import os
            if os.getenv("PHOENIX_ENABLED") != "true":
                return func(*args, **kwargs)
            
            with tracer.start_as_current_span(f"llm.call.{model}") as span:
                # Set model info
                span.set_attribute("llm.model", model)
                span.set_attribute("llm.provider", "ollama")
                
                # Capture GPU state before
                gpu_before = get_gpu_attributes()
                for key, value in gpu_before.items():
                    span.set_attribute(f"{key}.before", value)
                
                # Extract prompt
                prompt = kwargs.get("prompt", args[0] if args else "")
                span.set_attribute("llm.prompt", prompt[:500])
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Capture GPU state after
                    gpu_after = get_gpu_attributes()
                    for key, value in gpu_after.items():
                        span.set_attribute(f"{key}.after", value)
                    
                    # Calculate memory delta
                    if "gpu.memory_used_mb" in gpu_before and "gpu.memory_used_mb" in gpu_after:
                        delta = gpu_after["gpu.memory_used_mb"] - gpu_before["gpu.memory_used_mb"]
                        span.set_attribute("gpu.memory_delta_mb", delta)
                    
                    # LLM metrics
                    if isinstance(result, dict):
                        tokens = result.get("eval_count", 0)
                        eval_duration = result.get("eval_duration", 0) / 1e9  # ns to s
                        
                        span.set_attribute("llm.tokens", tokens)
                        span.set_attribute("llm.eval_duration_ms", eval_duration * 1000)
                        span.set_attribute("llm.tokens_per_second", 
                            tokens / eval_duration if eval_duration > 0 else 0)
                    
                    span.set_attribute("llm.latency_ms", latency_ms)
                    span.set_attribute("llm.status", "success")
                    
                    return result
                    
                except Exception as e:
                    span.set_attribute("llm.status", "error")
                    span.set_attribute("llm.error", str(e))
                    raise
        
        return wrapper
    return decorator
```

### Real-time Dashboard

```python
# src/monitoring/dashboard.py

import time
import os
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import BarColumn, Progress, TextColumn

from .gpu import GPUMonitor


console = Console()


class GPUDashboard:
    """Real-time GPU monitoring dashboard."""
    
    def __init__(self, refresh_rate: float = 1.0):
        self.refresh_rate = refresh_rate
        self.monitor = GPUMonitor()
        self.monitor.initialize()
        
        # Stats tracking
        self.request_count = 0
        self.error_count = 0
        self.tokens_generated = 0
        self.latencies = []
    
    def record_request(self, tokens: int, latency_ms: float, error: bool = False):
        """Record LLM request stats."""
        self.request_count += 1
        self.tokens_generated += tokens
        self.latencies.append(latency_ms)
        if error:
            self.error_count += 1
        
        # Keep last 100 latencies
        self.latencies = self.latencies[-100:]
    
    def _get_percentile(self, data: list, p: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def _generate_layout(self) -> Layout:
        """Generate dashboard layout."""
        metrics = self.monitor.get_metrics()
        
        layout = Layout()
        layout.split_column(
            Layout(name="gpu", size=8),
            Layout(name="stats", size=6),
        )
        
        # GPU Panel
        if metrics:
            gpu_table = Table(show_header=False, box=None, padding=(0, 2))
            gpu_table.add_column("Metric", style="cyan")
            gpu_table.add_column("Value", style="green")
            gpu_table.add_column("Bar", style="blue")
            
            # VRAM
            vram_percent = metrics.memory_utilization_percent
            vram_bar = "█" * int(vram_percent / 5) + "░" * (20 - int(vram_percent / 5))
            gpu_table.add_row(
                f"VRAM",
                f"{metrics.memory_used_mb:.0f} / {metrics.memory_total / (1024**2):.0f} MB",
                f"[blue]{vram_bar}[/blue] {vram_percent:.0f}%"
            )
            
            # Utilization
            util_bar = "█" * int(metrics.utilization_gpu / 5) + "░" * (20 - int(metrics.utilization_gpu / 5))
            gpu_table.add_row(
                f"GPU Util",
                f"{metrics.utilization_gpu:.0f}%",
                f"[green]{util_bar}[/green]"
            )
            
            # Temperature
            temp_bar = "█" * int(metrics.temperature / 5) + "░" * (20 - int(metrics.temperature / 5))
            temp_color = "red" if metrics.temperature > 80 else "yellow" if metrics.temperature > 70 else "green"
            gpu_table.add_row(
                f"Temp",
                f"{metrics.temperature}°C",
                f"[{temp_color}]{temp_bar}[/{temp_color}]"
            )
            
            # Power
            power_w = metrics.power_draw / 1000
            power_limit_w = metrics.power_limit / 1000
            power_percent = (metrics.power_draw / metrics.power_limit) * 100 if metrics.power_limit > 0 else 0
            power_bar = "█" * int(power_percent / 5) + "░" * (20 - int(power_percent / 5))
            gpu_table.add_row(
                f"Power",
                f"{power_w:.0f} / {power_limit_w:.0f} W",
                f"[magenta]{power_bar}[/magenta]"
            )
            
            layout["gpu"].update(
                Panel(gpu_table, title=f"GPU: {metrics.device_name}", border_style="blue")
            )
        else:
            layout["gpu"].update(Panel("GPU metrics unavailable", title="GPU", border_style="red"))
        
        # Stats Panel
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        stats_table.add_row("Requests", f"{self.request_count}")
        stats_table.add_row("Tokens", f"{self.tokens_generated}")
        
        if self.latencies:
            avg_latency = sum(self.latencies) / len(self.latencies)
            p50 = self._get_percentile(self.latencies, 50)
            p95 = self._get_percentile(self.latencies, 95)
            p99 = self._get_percentile(self.latencies, 99)
            
            stats_table.add_row("Latency (avg)", f"{avg_latency:.0f} ms")
            stats_table.add_row("Latency (p50/p95/p99)", f"{p50:.0f} / {p95:.0f} / {p99:.0f} ms")
            
            if self.latencies:
                avg_tokens_per_sec = self.tokens_generated / (sum(self.latencies) / 1000) if sum(self.latencies) > 0 else 0
                stats_table.add_row("Throughput", f"{avg_tokens_per_sec:.1f} tok/s")
        
        if self.request_count > 0:
            error_rate = (self.error_count / self.request_count) * 100
            stats_table.add_row("Errors", f"{self.error_count} ({error_rate:.1f}%)")
        
        layout["stats"].update(
            Panel(stats_table, title="LLM Stats (last 100 requests)", border_style="green")
        )
        
        return layout
    
    def run(self):
        """Run the dashboard."""
        try:
            with Live(
                self._generate_layout(),
                console=console,
                refresh_per_second=1 / self.refresh_rate,
            ) as live:
                while True:
                    time.sleep(self.refresh_rate)
                    live.update(self._generate_layout())
        except KeyboardInterrupt:
            pass
        finally:
            self.monitor.shutdown()


def run_dashboard():
    """Entry point to run dashboard."""
    dashboard = GPUDashboard()
    dashboard.run()


if __name__ == "__main__":
    run_dashboard()
```

### Module Init

```python
# src/monitoring/__init__.py

import os
from .gpu import GPUMonitor, get_gpu_monitor
from .cuda import get_cuda_metrics, reset_cuda_stats
from .telemetry import trace_llm_with_gpu, get_gpu_attributes
from .dashboard import GPUDashboard


def setup_monitoring(
    phoenix_enabled: bool = None,
    gpu_monitoring: bool = None,
):
    """Initialize monitoring subsystems."""
    
    # Use environment variables if not specified
    if phoenix_enabled is None:
        phoenix_enabled = os.getenv("PHOENIX_ENABLED", "false").lower() == "true"
    if gpu_monitoring is None:
        gpu_monitoring = os.getenv("GPU_MONITORING", "false").lower() == "true"
    
    if gpu_monitoring:
        monitor = get_gpu_monitor()
        if monitor:
            print("✅ GPU monitoring initialized")
        else:
            print("⚠️ GPU monitoring failed to initialize")
    
    return {
        "phoenix_enabled": phoenix_enabled,
        "gpu_monitoring": gpu_monitoring,
    }


__all__ = [
    "GPUMonitor",
    "get_gpu_monitor",
    "get_cuda_metrics",
    "reset_cuda_stats",
    "trace_llm_with_gpu",
    "get_gpu_attributes",
    "GPUDashboard",
    "setup_monitoring",
]
```

---

## Usage

### Enable Monitoring

```bash
# Environment variables
export PHOENIX_ENABLED=true      # Enable Phoenix traces
export GPU_MONITORING=true       # Enable GPU metrics
```

### Run Dashboard

```bash
# Standalone dashboard
python -m src.monitoring.dashboard
```

### Integrate with LLM Calls

```python
from src.monitoring import trace_llm_with_gpu

@trace_llm_with_gpu(model="granite3.3:2b")
def generate_response(prompt: str) -> dict:
    # ... Ollama API call ...
    return response
```

### Programmatic Usage

```python
from src.monitoring import get_gpu_monitor, get_cuda_metrics

# Get GPU metrics
gpu = get_gpu_monitor()
if gpu:
    metrics = gpu.get_metrics()
    print(f"GPU: {metrics.utilization_gpu}%")
    print(f"VRAM: {metrics.memory_used_mb:.0f} MB")
    print(f"Temp: {metrics.temperature}°C")

# Get CUDA metrics
cuda = get_cuda_metrics()
if cuda:
    print(f"CUDA allocated: {cuda.memory_allocated_mb:.0f} MB")
```

---

## Dashboard Output

```
┌──────────────────────────────────────────────────────────────────┐
│ GPU: NVIDIA GeForce RTX 3080                                     │
├──────────────────────────────────────────────────────────────────┤
│ VRAM      4,230 / 10,240 MB  ████████░░░░░░░░░░░░ 41%           │
│ GPU Util  87%               ██████████████████░░░               │
│ Temp      72°C              ████████████░░░░░░░░                │
│ Power     285 / 320 W       █████████████████░░░                │
├──────────────────────────────────────────────────────────────────┤
│ LLM Stats (last 100 requests)                                    │
├──────────────────────────────────────────────────────────────────┤
│ Requests          23                                             │
│ Tokens            2,847                                          │
│ Latency (avg)     890 ms                                         │
│ Latency (p50/p95/p99)  850 / 1,200 / 2,100 ms                   │
│ Throughput        124.5 tok/s                                    │
│ Errors            0 (0.0%)                                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phoenix UI Integration

When `PHOENIX_ENABLED=true`, GPU metrics appear as span attributes:

### Span Attributes

| Attribute | Example Value |
|-----------|---------------|
| `llm.model` | `granite3.3:2b` |
| `llm.tokens` | `128` |
| `llm.tokens_per_second` | `154.7` |
| `gpu.utilization_percent.before` | `15.0` |
| `gpu.utilization_percent.after` | `87.0` |
| `gpu.memory_used_mb.before` | `2100.0` |
| `gpu.memory_used_mb.after` | `4230.0` |
| `gpu.memory_delta_mb` | `2130.0` |
| `gpu.temperature_c.after` | `72` |

### Phoenix Query Examples

```sql
-- Find high-memory operations
span.attributes["gpu.memory_delta_mb"] > 1000

-- Find slow requests
span.attributes["llm.latency_ms"] > 2000

-- Find high GPU utilization
span.attributes["gpu.utilization_percent.after"] > 90
```

---

## CLI Tools (Quick Debugging)

### nvidia-smi

```bash
# Watch mode
watch -n 1 nvidia-smi

# JSON output
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,temperature.gpu --format=csv
```

### nvtop

```bash
# Install
sudo apt install nvtop

# Run
nvtop
```

### Ollama Status

```bash
# Show loaded models
docker exec parallax-ollama ollama ps

# Model memory usage
docker exec parallax-ollama ollama list
```

---

## Troubleshooting

### NVML Not Available

```bash
# Check NVIDIA driver
nvidia-smi

# Check pynvml installation
python -c "import pynvml; pynvml.nvmlInit(); print('OK')"
```

### GPU Monitoring Disabled

Ensure environment variable is set:
```bash
export GPU_MONITORING=true
```

### High Memory Usage

If monitoring causes memory issues:
```python
# Reduce refresh rate
dashboard = GPUDashboard(refresh_rate=2.0)  # 2 seconds
```

### Missing Metrics in Phoenix

- Ensure `PHOENIX_ENABLED=true`
- Check Phoenix is running: `curl http://localhost:4318`
- Verify OTLP endpoint in code

---

## Related Files

- [plans/observability.md](observability.md) - Phoenix + OpenTelemetry setup
- [plans/docker.md](docker.md) - Docker architecture
- [plans/models.md](models.md) - Model configuration
