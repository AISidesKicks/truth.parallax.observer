#!/bin/bash
# parallax.observer - Unified startup script
# Usage: ./up.sh [profile1] [profile2] ...
# No args: starts llm + embed + viking + phoenix + app
# Special: ./up.sh dev (starts llm + embed + viking + phoenix + dev)
# Profiles: llm, embed, viking, phoenix, app, dev

set -e

cd "$(dirname "$0")"

if [ $# -eq 0 ]; then
    PROFILES="llm viking phoenix app"
else
    case "$1" in
        dev)  PROFILES="llm viking phoenix dev" ;;
        *)    PROFILES="$@" ;;
    esac
fi

echo -e "\n=== parallax.observer Docker ==="
echo "Starting profiles: ${PROFILES[*]}"

PROFILE_ARGS=""
for profile in $PROFILES; do
    PROFILE_ARGS="$PROFILE_ARGS --profile $profile"
done

docker compose $PROFILE_ARGS up -d

echo -e "\n=== Waiting for services ==="
sleep 3

if [[ " $PROFILES " =~ " llm " ]]; then
    echo -e "\n=== Model server (llama.cpp router) ==="
    curl -s http://localhost:${LLM_PORT:-11433}/v1/models | head -30 \
        || echo "llm not reachable yet, check: docker logs prlx-llm"
fi

if [[ " $PROFILES " =~ " embed " ]]; then
    echo -e "\n=== Standalone embedding server ==="
    curl -s http://localhost:${EMBED_PORT:-7997}/v1/models | head -20 \
        || echo "embed not reachable yet, check: docker logs prlx-embed"
fi

if [[ " $PROFILES " =~ " viking " ]]; then
    echo -e "\n=== OpenViking context server ==="
    curl -s http://localhost:${VIKING_PORT:-1933}/health \
        || echo "viking not reachable yet, check: docker logs prlx-viking"
fi

echo -e "\n=== Status ==="
docker ps --filter "name=prlx-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
