#!/usr/bin/env python3
"""
Test Qwen3-VL:2B Vision-Language Model capabilities via Ollama API.

Tests image understanding with base64-encoded images.
"""
import base64
import time
from pathlib import Path

import requests

OLLAMA_HOST = "http://localhost:11433"
MODEL = "qwen3-vl:2b"

def encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def test_vision(image_path: str, prompt: str) -> dict:
    """Test vision model with an image."""
    image_base64 = encode_image(image_path)
    
    start = time.time()
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 256,
            }
        },
        timeout=120,
    )
    latency = time.time() - start
    
    response.raise_for_status()
    result = response.json()
    
    return {
        "latency_sec": latency,
        "response": result.get("response", ""),
        "tokens": result.get("eval_count", 0),
        "tokens_per_sec": result.get("eval_count", 0) / latency if latency > 0 else 0,
    }

def main():
    print(f"\n{'='*70}")
    print(" Qwen3-VL:2B Vision-Language Model Test")
    print(f"{'='*70}")
    
    test_images = [
        ("www/logo-small.jpg", "What do you see in this image? Describe it briefly."),
        ("www/logo-full.png", "What is shown in this image? What text or symbols can you identify?"),
    ]
    
    for image_path, prompt in test_images:
        if not Path(image_path).exists():
            print(f"\nSkipping {image_path} - not found")
            continue
            
        print(f"\n--- Testing: {image_path} ---")
        print(f"Prompt: {prompt}")
        
        try:
            result = test_vision(image_path, prompt)
            print(f"Latency: {result['latency_sec']:.2f}s")
            print(f"Tokens: {result['tokens']} ({result['tokens_per_sec']:.1f} tok/s)")
            print(f"Response:\n{result['response'][:1000]}")
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"\n{'='*70}")
    print(" Test Complete")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
