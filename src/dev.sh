#!/bin/bash
# Development helper script for parallax.observer APP

# Activate conda environment and run command
# Usage: ./dev.sh [command]
# Examples:
#   ./dev.sh pytest tests/ -v
#   ./dev.sh uvicorn parallax_observer.main:app --reload

cd "$(dirname "$0")"

if [ -z "$1" ]; then
    echo "Usage: ./dev.sh [command]"
    echo "Examples:"
    echo "  ./dev.sh pytest tests/ -v"
    echo "  ./dev.sh uvicorn parallax_observer.main:app --reload --port 8008"
    exit 1
fi

PYTHONPATH=src conda run -n parallax.observer "$@"
