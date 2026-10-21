#!/bin/bash
# parallax.observer - Stop all containers

set -e

cd "$(dirname "$0")"

echo -e "\n=== Stopping parallax.observer containers ==="

docker compose --env-file ../.env -f docker-compose.yml --profile llm --profile embed --profile viking --profile phoenix --profile app --profile dev down 2>/dev/null || true

echo -e "\n=== Stopped ==="
docker ps --filter "name=prlx-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "No prlx containers running"
