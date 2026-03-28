#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if python -c "import fastapi" &> /dev/null; then
    echo "FastAPI is installed. Running server"
    fastapi dev "${ROOT_DIR}/apps/api/src/main.py"
else
    echo "FastAPI is not installed. Please install it using:"
    echo "uv add fastapi --extra standard"
fi
