#!/bin/bash
# parallax.observer - Container status check

cd "$(dirname "$0")"

echo -e "\n=== parallax.observer Status ==="

echo -e "\n--- Containers ---"
# plain docker ps, the services sit behind compose profiles and compose ps
# only shows the ones of the profiles that are named
docker ps --filter "name=prlx-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
if [ -z "$(docker ps -q --filter 'name=prlx-')" ]; then
    echo "nothing is running, start it with ./up.sh"
fi

echo -e "\n--- Network ---"
docker network ls | grep prlx-lab || echo "prlx-lab network not found"

echo -e "\n--- Endpoints ---"
echo "Chat (llama.cpp):  http://localhost:${LLM_PORT:-11433}/v1"
echo "Embeddings:        http://localhost:${EMBED_PORT:-7997}/v1"
echo "OpenViking:        http://localhost:${VIKING_PORT:-1933}"
echo "Phoenix:           http://localhost:6006"
echo "App:               http://localhost:8668"

echo -e "\n--- GPU ---"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
        --format=csv,noheader 2>/dev/null || echo "nvidia-smi failed"
else
    echo "nvidia-smi not available"
fi
