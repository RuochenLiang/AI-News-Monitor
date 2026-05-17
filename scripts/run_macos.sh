#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${AI_NEWS_MONITOR_VENV:-$HOME/.venvs/ai-news-monitor}"
PYTHON_BIN="$VENV_DIR/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  "$ROOT_DIR/scripts/bootstrap_macos.sh"
fi

cd "$ROOT_DIR"
exec "$PYTHON_BIN" main.py
