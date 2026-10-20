#!/bin/bash
# Development helper for the parallax.observer app.
#
# Runs a command inside the pixi environment from the project root.
#
# Usage: ./dev.sh [command]
# Examples:
#   ./dev.sh pytest tests/ -v
#   ./dev.sh python -m uvicorn src.main:app --reload --port 8668

cd "$(dirname "$0")/.."

if [ -z "$1" ]; then
    echo "Usage: ./dev.sh [command]"
    echo "Examples:"
    echo "  ./dev.sh pytest tests/ -v"
    echo "  ./dev.sh python -m uvicorn src.main:app --reload --port 8668"
    exit 1
fi

if [ "$1" = "pytest" ]; then
    # the test tooling lives in the experiment environment
    exec pixi run --environment experiment "$@"
fi

exec pixi run "$@"
