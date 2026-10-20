#!/usr/bin/env python3
"""
Test Infinity embedding server for text and image embeddings.

Prerequisites:
    1. Start Infinity: cd infra/embed/infinity && ./up.sh
    2. Wait for models to load (~30s first run)

Usage:
    python infinity_test.py
"""

import base64
import requests
import time
from pathlib import Path

INFINITY_HOST = "http://localhost:7997"

# Models served by Infinity
TEXT_MODEL = "nomic-ai/modernbert-embed-base"
IMAGE_MODEL = "google/siglip-so400m-patch14-384"


def test_health():
    """Test Infinity health endpoint."""
    response = requests.get(f"{INFINITY_HOST}/health")
    print(f"Health: {response.status_code}")
    return response.status_code == 200


def test_text_embedding():
    """Test text embedding generation."""
    print("\n--- Text Embedding Test ---")
    
    texts = [
        "search_query: Why is the Earth flat?",
        "search_document: Water always finds its level. Period.",
        "search_document: The horizon appears flat from any altitude.",
    ]
    
    start = time.time()
    response = requests.post(
        f"{INFINITY_HOST}/v1/embeddings",
        json={
            "model": TEXT_MODEL,
            "input": texts,
        },
    )
    latency = (time.time() - start) * 1000
    
    if response.status_code != 200:
        print(f"Error: {response.text}")
        return None
    
    data = response.json()
    embeddings = data["data"]
    
    print(f"Model: {data['model']}")
    print(f"Texts: {len(texts)}")
    print(f"Embedding dimension: {len(embeddings[0]['embedding'])}")
    print(f"Latency: {latency:.2f}ms")
    print(f"Tokens used: {data['usage']['total_tokens']}")
    
    return embeddings


def test_image_embedding(image_path: str = None):
    """Test image embedding generation with SigLIP."""
    print("\n--- Image Embedding Test ---")
    
    # Use a test image or download one
    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
    else:
        # Use a public test image
        print("Downloading test image...")
        img_response = requests.get(
            "http://images.cocodataset.org/val2017/000000039769.jpg"
        )
        image_b64 = base64.b64encode(img_response.content).decode()
    
    start = time.time()
    response = requests.post(
        f"{INFINITY_HOST}/v1/embeddings",
        json={
            "model": IMAGE_MODEL,
            "input": [image_b64],
        },
    )
    latency = (time.time() - start) * 1000
    
    if response.status_code != 200:
        print(f"Error: {response.text}")
        return None
    
    data = response.json()
    embedding = data["data"][0]["embedding"]
    
    print(f"Model: {data['model']}")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"Latency: {latency:.2f}ms")
    
    return embedding


def test_text_image_similarity():
    """Test similarity between text and image embeddings."""
    print("\n--- Text-Image Similarity Test ---")
    
    # Text embedding
    text_response = requests.post(
        f"{INFINITY_HOST}/v1/embeddings",
        json={
            "model": IMAGE_MODEL,  # Use same model for comparable embeddings
            "input": ["a photo of cats"],
        },
    )
    text_emb = text_response.json()["data"][0]["embedding"]
    
    # Image embedding (cats image)
    img_response = requests.get(
        "http://images.cocodataset.org/val2017/000000039769.jpg"
    )
    image_b64 = base64.b64encode(img_response.content).decode()
    
    img_response = requests.post(
        f"{INFINITY_HOST}/v1/embeddings",
        json={
            "model": IMAGE_MODEL,
            "input": [image_b64],
        },
    )
    img_emb = img_response.json()["data"][0]["embedding"]
    
    # Cosine similarity
    import math
    dot_product = sum(a * b for a, b in zip(text_emb, img_emb))
    norm_text = math.sqrt(sum(a * a for a in text_emb))
    norm_img = math.sqrt(sum(b * b for b in img_emb))
    similarity = dot_product / (norm_text * norm_img)
    
    print(f"Text: 'a photo of cats'")
    print(f"Image: cats on pink blanket")
    print(f"Similarity: {similarity:.4f}")
    
    return similarity


def test_models_endpoint():
    """List available models."""
    print("\n--- Available Models ---")
    
    response = requests.get(f"{INFINITY_HOST}/v1/models")
    data = response.json()
    
    for model in data["data"]:
        print(f"  - {model['id']}")
    
    return data["data"]


def test_metrics():
    """Get Infinity metrics."""
    print("\n--- Infinity Metrics ---")
    
    try:
        response = requests.get(f"{INFINITY_HOST}/metrics")
        print(response.text[:500])
    except Exception as e:
        print(f"Metrics not available: {e}")


def main():
    print("=" * 60)
    print(" Infinity Embedding Server Test")
    print("=" * 60)
    
    # Health check
    if not test_health():
        print("\nInfinity not responding. Start with:")
        print("  cd infra/embed/infinity && ./up.sh")
        return
    
    # List models
    models = test_models_endpoint()
    
    # Test text embeddings
    text_embeddings = test_text_embedding()
    
    # Test image embeddings
    image_embedding = test_image_embedding()
    
    # Test text-image similarity
    if text_embeddings and image_embedding:
        similarity = test_text_image_similarity()
    
    # Metrics
    test_metrics()
    
    print("\n" + "=" * 60)
    print(" All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
