#!/bin/bash
# parallax.observer - fetch the GGUF models used by the llama.cpp services
#
# The llama.cpp services mount .models/llama read-only, so the files have to
# be there before the containers start.
#
# Usage: ./fetch-models.sh [--llm] [--embed]

set -euo pipefail

cd "$(dirname "$0")/.."

MODEL_DIR="${MODEL_DIR:-.models/llama}"

LLM_REPO="${LLM_REPO:-ibm-granite/granite-4.0-h-tiny-GGUF}"
LLM_FILE="${LLM_FILE:-granite-4.0-h-tiny-Q4_K_M.gguf}"
EMBED_REPO="${EMBED_REPO:-ggml-org/embeddinggemma-2-GGUF}"
EMBED_FILE="${EMBED_FILE:-embeddinggemma-2-Q8_0.gguf}"
# the vision projector, the encoder needs it next to the model or the image
# tier does not work
MMPROJ_REPO="${MMPROJ_REPO:-ggml-org/embeddinggemma-2-GGUF}"
MMPROJ_FILE="${MMPROJ_FILE:-mmproj-embeddinggemma-2-Q8_0.gguf}"

DO_LLM=1
DO_EMBED=1
if [ $# -gt 0 ]; then
    DO_LLM=0
    DO_EMBED=0
    for arg in "$@"; do
        case "$arg" in
            --llm)   DO_LLM=1 ;;
            --embed) DO_EMBED=1 ;;
            *) echo "unknown option: $arg" >&2; exit 1 ;;
        esac
    done
fi

mkdir -p "$MODEL_DIR"

fetch() {
    local repo="$1" file="$2" dest="$MODEL_DIR/$2"
    if [ -f "$dest" ]; then
        echo "  already there: $file"
        return 0
    fi
    echo "  fetching $file from $repo"
    curl -fL --retry 3 --retry-delay 2 -C - \
        -o "$dest" \
        "https://huggingface.co/${repo}/resolve/main/${file}?download=true"
}

echo "=== parallax.observer model fetch ==="
echo "target: $MODEL_DIR"

if [ "$DO_LLM" -eq 1 ]; then
    echo "- chat model"
    fetch "$LLM_REPO" "$LLM_FILE"
fi

if [ "$DO_EMBED" -eq 1 ]; then
    echo "- embedding model"
    fetch "$EMBED_REPO" "$EMBED_FILE"
    echo "- vision projector"
    fetch "$MMPROJ_REPO" "$MMPROJ_FILE"
fi

echo -e "\n=== Done ==="
ls -lh "$MODEL_DIR"
