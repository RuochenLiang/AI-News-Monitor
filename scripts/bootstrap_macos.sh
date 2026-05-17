#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV_DIR="${AI_NEWS_MONITOR_VENV:-$HOME/.venvs/ai-news-monitor}"

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("AI News Monitor requires Python 3.11 or newer.")
PY

rm -rf "$VENV_DIR"
mkdir -p "$(dirname "$VENV_DIR")"

"$PYTHON_BIN" -m venv "$VENV_DIR"

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install -r requirements.txt
"$VENV_DIR/bin/python" -m pip check
"$VENV_DIR/bin/python" - <<'PY'
import sys
from src.app import _configure_qt_runtime
from PySide6.QtWidgets import QApplication

_configure_qt_runtime()
app = QApplication(sys.argv)
print("qt ok")
PY

echo "Bootstrap complete: $VENV_DIR"
