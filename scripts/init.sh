#!/bin/bash
set -e

# Define directories
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
CONFIG_DIR="$ROOT_DIR/codex"
MEMORY_DIR="$CONFIG_DIR/memory"
LOG_DIR="$CONFIG_DIR/logs"

# Ensure required directories exist
mkdir -p "$CONFIG_DIR"
mkdir -p "$MEMORY_DIR"
mkdir -p "$LOG_DIR"

# Create virtual environment if needed
if [ ! -d "$ROOT_DIR/.venv" ]; then
  echo "[INFO] Creating Python virtual environment..."
  set +e
  python3 -m venv "$ROOT_DIR/.venv"
  VENV_STATUS=$?
  set -e
  if [ $VENV_STATUS -ne 0 ]; then
    echo "[WARN] Failed to create venv (ensurepip missing?). On Debian/Ubuntu: sudo apt install python3-venv"
    echo "[INFO] Continuing without a virtual environment."
  else
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/bin/activate"
    pip install --upgrade pip
    if [ -f "$ROOT_DIR/requirements.txt" ]; then
      pip install -r "$ROOT_DIR/requirements.txt"
    else
      echo "[INFO] No requirements.txt found; skipping pip install."
    fi
  fi
else
  echo "[INFO] Virtual environment already exists."
fi

# Check for config.json
if [ ! -f "$CONFIG_DIR/config.json" ]; then
  echo "[WARN] No config.json found in codex/. Please create one or run the generator script."
else
  echo "[INFO] config.json found."
fi

# Final status message
echo "[✅] Codex CLI initialized successfully."
