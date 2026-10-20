#!/usr/bin/env python3
"""
Ollama Model Benchmark for parallax.observer

Tests GGUF models via Ollama API with:
- Model load time and memory usage
- 20 generation requests per model
- Tokens per second measurement
- GPU memory tracking throughout

Models tested (Q4_K_M quantization):
- granite4:micro-h (2.0 GB)
- granite4:tiny-h (4.0 GB)
- granite3.3:2b (1.5 GB, reasoning model)

Prerequisites:
    1. Start Ollama container: ./infra/aiserve/ollama/up.sh
    2. Models are pulled automatically by up.sh

Usage:
    cd investigations/ollama && python3 benchmark.py
"""

import gc
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Configuration
NUM_REQUESTS = 20
MAX_TOKENS = 128
TEMPERATURE = 0.7
OLLAMA_HOST = "http://localhost:11433"
NUM_CTX = 4096  # Context window for inference

# Models to test (from Ollama library)
MODELS = [
    ("granite4:micro-h", "Granite-4.0-Micro-H", 2.0),
    ("granite4:tiny-h", "Granite-4.0-Tiny-H", 4.0),
    ("granite3.3:2b", "Granite-3.3-2B-Reasoning", 1.5),
]

# Test prompts (persuasion-themed for parallax.observer)
TEST_PROMPTS = [
    "Explain why some people believe the Earth is flat.",
    "What evidence supports a spherical Earth?",
    "How would you persuade someone that the Earth is round?",
    "What are the main arguments of flat Earth believers?",
    "Explain the concept of gravity in simple terms.",
    "Why do ships disappear hull-first over the horizon?",
    "What is the circumference of the Earth and how was it measured?",
    "How do airplanes navigate on a spherical Earth?",
    "Explain why Antarctica is a continent, not an ice wall.",
    "What would happen if the Earth were actually flat?",
    "How do satellites orbit a spherical planet?",
    "Why do different stars appear in the northern and southern hemispheres?",
    "Explain time zones on a round Earth.",
    "What is the Coriolis effect and how does it prove Earth's rotation?",
    "How do lunar eclipses demonstrate Earth's shape?",
    "Why don't we feel the Earth spinning?",
    "Explain the Bedford Level Experiment and its flaws.",
    "How does GPS work on a spherical Earth?",
    "What experiments can you do at home to verify Earth's shape?",
    "Why do flat Earth maps distort continent sizes?",
]


@dataclass
class ModelBenchmarkResult:
    """Results for a single model benchmark"""
    model_id: str
    model_name: str
    engine: str
    model_size_gb: float
    initial_memory_gib: float
    load_time_sec: float
    memory_after_load_gib: float
    peak_memory_gib: float
    requests: list[dict[str, Any]]
    total_tokens: int
    total_time_sec: float
    avg_tokens_per_sec: float
    avg_latency_ms: float
    requests_completed: int
    success: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_gpu_memory_gib() -> float:
    """Get current GPU memory allocated in GiB"""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024**3)
    except:
        pass
    return 0.0


def get_gpu_memory_reserved_gib() -> float:
    """Get current GPU memory reserved in GiB"""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_reserved() / (1024**3)
    except:
        pass
    return 0.0


def get_gpu_memory_free_gib() -> float:
    """Get free GPU memory in GiB"""
    try:
        import torch
        if torch.cuda.is_available():
            total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            return total - reserved
    except:
        pass
    return 0.0


def clear_gpu_memory():
    """Aggressively clear GPU memory"""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
    except:
        pass
    gc.collect()
    time.sleep(2)


def check_ollama_running() -> bool:
    """Check if Ollama server is running"""
    import requests
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        return resp.status_code == 200
    except:
        return False


def ollama_generate(model: str, prompt: str, timeout: int = 120) -> dict[str, Any]:
    """Generate response using Ollama API"""
    import requests
    
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
                "num_ctx": NUM_CTX,
            }
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def ollama_load_model(model: str) -> bool:
    """Load a model into Ollama memory (generate empty prompt)"""
    try:
        # Send empty prompt to load model
        import requests
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": "",
                "stream": False,
                "options": {"num_predict": 1}
            },
            timeout=300,  # 5 minutes for model loading
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"      Error loading model: {e}")
        return False


def ollama_unload_model(model: str) -> bool:
    """Unload model from Ollama memory"""
    try:
        import requests
        # Keep model loaded = false
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "keep_alive": 0,  # Unload immediately
            },
            timeout=30,
        )
        return True
    except:
        return False


def benchmark_model(model_id: str, model_name: str, model_size_gb: float) -> ModelBenchmarkResult:
    """Benchmark a single model with Ollama"""
    print(f"\n{'='*70}")
    print(f" Ollama Benchmark: {model_name}")
    print(f" Model ID: {model_id}")
    print(f" Size: {model_size_gb} GB")
    print(f"{'='*70}")
    
    load_time = 0.0
    initial_memory = 0.0
    memory_after_load = 0.0
    peak_memory = 0.0
    requests_metrics = []
    total_tokens = 0
    total_time = 0.0
    
    try:
        # Clear GPU before starting
        print("\n[1/4] Clearing GPU memory...")
        clear_gpu_memory()
        initial_memory = get_gpu_memory_reserved_gib()
        print(f"      Initial GPU reserved: {initial_memory:.2f} GiB")
        print(f"      GPU free: {get_gpu_memory_free_gib():.2f} GiB")
        
        # Load model (first request loads it)
        print("\n[2/4] Loading model...")
        start_time = time.time()
        
        if not ollama_load_model(model_id):
            raise RuntimeError("Failed to load model in Ollama")
        
        load_time = time.time() - start_time
        memory_after_load = get_gpu_memory_reserved_gib()
        peak_memory = memory_after_load
        print(f"      Model loaded in {load_time:.2f}s")
        print(f"      GPU memory after load: {memory_after_load:.2f} GiB")
        
        # Run benchmark requests
        print(f"\n[3/4] Running {NUM_REQUESTS} requests...")
        
        for i, prompt in enumerate(TEST_PROMPTS[:NUM_REQUESTS]):
            req_start = time.time()
            
            try:
                result = ollama_generate(model_id, prompt)
                
                # Get token count from Ollama response
                generated_tokens = result.get("eval_count", 0)
                total_tokens += generated_tokens
                
                latency = (time.time() - req_start) * 1000
                tokens_per_sec = generated_tokens / (latency / 1000) if latency > 0 else 0
                current_memory = get_gpu_memory_reserved_gib()
                peak_memory = max(peak_memory, current_memory)
                
                requests_metrics.append({
                    "request_num": i + 1,
                    "latency_ms": latency,
                    "tokens": generated_tokens,
                    "tokens_per_sec": tokens_per_sec,
                    "memory_gib": current_memory,
                    "success": True,
                })
                
                print(f"      [{i+1:2d}/{NUM_REQUESTS}] {latency:6.0f}ms, {generated_tokens:3d} tokens, {tokens_per_sec:5.1f} tok/s, mem: {current_memory:.2f} GiB")
                
            except Exception as e:
                requests_metrics.append({
                    "request_num": i + 1,
                    "latency_ms": 0,
                    "tokens": 0,
                    "tokens_per_sec": 0,
                    "memory_gib": get_gpu_memory_reserved_gib(),
                    "success": False,
                    "error": str(e),
                })
                print(f"      [{i+1:2d}/{NUM_REQUESTS}] FAILED: {e}")
        
        # Calculate aggregates
        successful_requests = [r for r in requests_metrics if r.get("success")]
        total_time = sum(r["latency_ms"] for r in successful_requests) / 1000
        avg_latency = sum(r["latency_ms"] for r in successful_requests) / len(successful_requests) if successful_requests else 0
        avg_tokens_per_sec = sum(r["tokens_per_sec"] for r in successful_requests) / len(successful_requests) if successful_requests else 0
        
        # Unload model
        print("\n[4/4] Unloading model...")
        ollama_unload_model(model_id)
        clear_gpu_memory()
        
        return ModelBenchmarkResult(
            model_id=model_id,
            model_name=model_name,
            engine="ollama",
            model_size_gb=model_size_gb,
            initial_memory_gib=initial_memory,
            load_time_sec=load_time,
            memory_after_load_gib=memory_after_load,
            peak_memory_gib=peak_memory,
            requests=requests_metrics,
            total_tokens=total_tokens,
            total_time_sec=total_time,
            avg_tokens_per_sec=avg_tokens_per_sec,
            avg_latency_ms=avg_latency,
            requests_completed=len(successful_requests),
            success=True,
        )
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on failure
        ollama_unload_model(model_id)
        clear_gpu_memory()
        
        return ModelBenchmarkResult(
            model_id=model_id,
            model_name=model_name,
            engine="ollama",
            model_size_gb=model_size_gb,
            initial_memory_gib=initial_memory,
            load_time_sec=load_time,
            memory_after_load_gib=memory_after_load,
            peak_memory_gib=peak_memory,
            requests=requests_metrics,
            total_tokens=total_tokens,
            total_time_sec=total_time,
            avg_tokens_per_sec=0,
            avg_latency_ms=0,
            requests_completed=len([r for r in requests_metrics if r.get("success")]),
            success=False,
            error=str(e),
        )


def print_results_table(results: list[ModelBenchmarkResult]):
    """Print results in a formatted table"""
    print(f"\n{'='*90}")
    print(" OLLAMA BENCHMARK RESULTS")
    print(f"{'='*90}")
    print(f"{'Model':<25} {'Size(GB)':<10} {'Load(s)':<10} {'Tok/s':<10} {'Latency':<10} {'Status'}")
    print(f"{'-'*90}")
    
    for r in results:
        status = "✅" if r.success else "❌"
        print(f"{r.model_name:<25} {r.model_size_gb:<10.1f} {r.load_time_sec:<10.1f} "
              f"{r.avg_tokens_per_sec:<10.1f} {r.avg_latency_ms:<10.0f} {status}")
    
    print(f"{'='*90}\n")


def main():
    print("\n" + "="*70)
    print(" Ollama Model Benchmark")
    print(" parallax.observer")
    print("="*70)
    print(f"\nRequests per model: {NUM_REQUESTS}")
    print(f"Max tokens per request: {MAX_TOKENS}")
    print(f"Temperature: {TEMPERATURE}")
    print(f"Context window: {NUM_CTX}")
    print(f"Ollama host: {OLLAMA_HOST}")
    
    # Check Ollama is running
    print("\nChecking Ollama server...")
    if not check_ollama_running():
        print("❌ Ollama server not running!")
        print("\nPlease start Ollama first:")
        print("  OLLAMA_FLASH_ATTENTION=1 ollama serve")
        return 1
    print("✅ Ollama server is running")
    
    print(f"\nModels to test: {len(MODELS)}")
    for mid, mname, msize in MODELS:
        print(f"  - {mname} ({mid}, {msize} GB)")
    
    results: list[ModelBenchmarkResult] = []
    
    # Run benchmark for each model
    for model_id, model_name, model_size in MODELS:
        result = benchmark_model(model_id, model_name, model_size)
        results.append(result)
        
        # Save incremental results
        output_file = Path(__file__).parent.parent / "benchmark_ollama_results.json"
        with open(output_file, "w") as f:
            json.dump({
                "engine": "ollama",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "config": {
                    "num_requests": NUM_REQUESTS,
                    "max_tokens": MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "num_ctx": NUM_CTX,
                    "ollama_host": OLLAMA_HOST,
                },
                "results": [r.to_dict() for r in results]
            }, f, indent=2)
        print(f"\n      Incremental results saved to: {output_file}")
    
    # Print summary
    print_results_table(results)
    
    # Final GPU state
    print("Final GPU state:")
    try:
        import torch
        if torch.cuda.is_available():
            total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            allocated = torch.cuda.memory_allocated() / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            print(f"  Total: {total:.2f} GiB")
            print(f"  Allocated: {allocated:.2f} GiB")
            print(f"  Reserved: {reserved:.2f} GiB")
            print(f"  Free: {total - reserved:.2f} GiB")
    except:
        print("  GPU not available")
    
    print(f"\n{'='*70}")
    print(" Benchmark Complete")
    print(f"{'='*70}")
    
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
