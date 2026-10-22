#!/bin/bash
# parallax.observer - Test script
# Tests the chat model with persuasion-themed prompts and the embedding
# server with a retrieval round trip.

set -e

cd "$(dirname "$0")"

LLM_PORT="${LLM_PORT:-11433}"
EMBED_PORT="${EMBED_PORT:-7997}"
VIKING_PORT="${VIKING_PORT:-1933}"
LLM_MODEL="${LLM_MODEL_ALIAS:-granite-4.0-h-tiny}"

echo -e "\n=== parallax.observer Tests ==="

echo -e "\n--- Checking the chat server ---"
if ! docker ps | grep -q prlx-llm; then
    echo "ERROR: prlx-llm container not running"
    echo "Start with: ./up.sh llm"
    exit 1
fi

echo -e "\n--- Model list ---"
curl -s "http://localhost:$LLM_PORT/v1/models" | head -30

PROMPT_1="Explain why some people believe the Earth is flat. What are their main arguments?"
PROMPT_2="How would you persuade a flat Earth believer that the Earth is actually spherical?"
PROMPT_3="What is the strongest evidence that proves the Earth is round?"

for prompt in "$PROMPT_1" "$PROMPT_2" "$PROMPT_3"; do
    echo -e "\n--- Prompt: $prompt ---"
    time curl -N -X POST "http://localhost:$LLM_PORT/v1/chat/completions" \
         -H "Content-Type: application/json" \
         -d "{\"model\": \"$LLM_MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}], \"stream\": false}"
    echo ""
done

echo -e "\n--- Embedding server ---"
if docker ps | grep -q prlx-embed; then
    curl -s -X POST "http://localhost:$EMBED_PORT/v1/embeddings" \
         -H "Content-Type: application/json" \
         -d "{\"model\": \"${EMBED_MODEL_ALIAS:-embeddinggemma-2}\", \"input\": [\"search_query: why is the earth flat\"]}" \
         | head -c 400
    echo -e "\n"
else
    echo "prlx-embed is not running, skipping"
fi

echo -e "\n--- OpenViking context server ---"
if docker ps | grep -q prlx-viking; then
    curl -s "http://localhost:$VIKING_PORT/health"
    echo ""
else
    echo "prlx-viking is not running, skipping"
fi

echo -e "\n--- The stack end to end ---"
# models, memory, corpus on disk, index and scoped retrieval, all of it
if command -v python >/dev/null 2>&1; then
    python ../scripts/verify_stack.py --llm "http://localhost:$LLM_PORT/v1" --server "http://localhost:$VIKING_PORT" || exit 1
else
    echo "python is not on the path, skipping the stack check"
fi

echo -e "\n"
echo "=========================================="
echo "=== All tests complete ==="
echo "=========================================="
echo -e "\n=== GPU status ==="
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader 2>/dev/null || echo "nvidia-smi failed"
