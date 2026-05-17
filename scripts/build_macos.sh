#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
BUILD_ROOT="${AI_NEWS_MONITOR_BUILD_ROOT:-$HOME/.cache/ai-news-monitor-build}"
DIST_DIR="$BUILD_ROOT/dist"
WORK_DIR="$BUILD_ROOT/build"
SPEC_DIR="$BUILD_ROOT/spec"
RELEASE_DIR="$BUILD_ROOT/release"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$PYTHON_BIN"
elif [[ -x "${AI_NEWS_MONITOR_VENV:-$HOME/.venvs/ai-news-monitor}/bin/python" ]]; then
  PYTHON_BIN="${AI_NEWS_MONITOR_VENV:-$HOME/.venvs/ai-news-monitor}/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3.11"
fi
"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("AI News Monitor packaging requires Python 3.11 or newer.")
PY

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r requirements.txt -r requirements-dev.txt
"$PYTHON_BIN" -m pytest

rm -rf build dist release "$BUILD_ROOT" AI-News-Monitor-macOS.zip
mkdir -p "$DIST_DIR" "$WORK_DIR" "$SPEC_DIR" "$RELEASE_DIR"
"$PYTHON_BIN" -m PyInstaller --noconfirm --windowed --name "AI News Monitor" \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  --specpath "$SPEC_DIR" \
  --add-data "$ROOT_DIR/config.example.yaml:." \
  --add-data "$ROOT_DIR/.env.example:." \
  --add-data "$ROOT_DIR/README.md:." \
  --add-data "$ROOT_DIR/README.zh-CN.md:." \
  --add-data "$ROOT_DIR/LICENSE:." \
  --add-data "$ROOT_DIR/AI_DISCLOSURE.md:." \
  --add-data "$ROOT_DIR/SOURCE_GUIDE.md:." \
  --add-data "$ROOT_DIR/NOTIFICATION_GUIDE.md:." \
  --add-data "$ROOT_DIR/locales:locales" \
  main.py

APP_PATH="$DIST_DIR/AI News Monitor.app"
find "$APP_PATH" -name ".DS_Store" -delete
xattr -cr "$APP_PATH" || true
codesign --force --deep --sign - "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

cp config.example.yaml .env.example README.md README.zh-CN.md LICENSE AI_DISCLOSURE.md SOURCE_GUIDE.md NOTIFICATION_GUIDE.md "$RELEASE_DIR/"
cp -R "$APP_PATH" "$RELEASE_DIR/"
find "$RELEASE_DIR" -name ".DS_Store" -delete
cd "$RELEASE_DIR"
zip -r "$ROOT_DIR/AI-News-Monitor-macOS.zip" . -x "*/.DS_Store"
