#!/usr/bin/env bash
set -e

echo "=== ProductFlow AI Setup ==="

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

# Create directories
mkdir -p database models sessions media-cache prompts pipelines logs backups

# Python backend
echo "[1/5] Setting up Python backend..."
python3 -m venv .venv 2>/dev/null || python -m venv .venv
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# Environment file
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "[2/5] Created backend/.env from example"
else
  echo "[2/5] backend/.env already exists"
fi

# Database
echo "[3/5] Initializing database..."
python -c "
from app.database.connection import init_db
init_db()
print('Database initialized at database/productflow.db')
"

# Model download
echo "[4/5] Downloading SmolLM2-135M GGUF..."
MODEL_DIR="models"
MODEL_FILE="$MODEL_DIR/smollm2-135m.gguf"
if [ ! -f "$MODEL_FILE" ]; then
  curl -L -o "$MODEL_FILE" \
    "https://huggingface.co/bartowski/SmolLM2-135M-GGUF/resolve/main/SmolLM2-135M-Q4_K_M.gguf"
  echo "Model downloaded to $MODEL_FILE"
else
  echo "Model already exists at $MODEL_FILE"
fi

# Swap (Pi Zero 2 W optimization)
echo "[5/5] Configuring swap (1024MB) and swappiness..."
if command -v dphys-swapfile &>/dev/null; then
  sudo dphys-swapfile swapoff
  sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
  sudo dphys-swapfile setup
  sudo dphys-swapfile swapon
  echo "Swap set to 1024MB"
else
  echo "Skipping swap config (not on Pi or dphys-swapfile not found)"
fi

# Set swappiness to 10 (prefer RAM, avoid SD card wear)
if [ -f /etc/sysctl.d/99-swappiness.conf ]; then
  echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
  sudo sysctl -w vm.swappiness=10
  echo "Swappiness set to 10"
else
  sudo sysctl -w vm.swappiness=10 2>/dev/null || true
fi

echo ""
echo "=== Setup complete ==="
echo "Run: scripts/start.sh"
