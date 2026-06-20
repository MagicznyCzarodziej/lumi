#!/usr/bin/env bash
# Launch Lumi from the desktop (no terminal). Requires `uv sync` in the repo first.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    if command -v uv >/dev/null 2>&1; then
        cd "$ROOT"
        uv sync
    else
        echo "Missing $PYTHON — run 'uv sync' in $ROOT first." >&2
        exit 1
    fi
fi

if [[ ! -x "$PYTHON" ]]; then
    echo "Missing $PYTHON after uv sync." >&2
    exit 1
fi

cd "$ROOT"
export LUMI_CONFIG="${LUMI_CONFIG:-$ROOT/config.yaml}"
exec "$PYTHON" -m lumi "$@"
