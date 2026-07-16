#!/usr/bin/env bash
set -e

echo "=== ProductFlow AI — Pi Zero 2 W Setup ==="

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

# Create directories
mkdir -p database models sessions media-cache prompts pipelines logs backups

# 1. System dependencies
echo "[1/8] Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip nodejs npm git curl build-essential

# 2. Python backend
echo "[2/8] Setting up Python backend..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install pyrogram tgcrypto

# 3. Environment file
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env 2>/dev/null || true
  echo "[3/8] Created backend/.env"
else
  echo "[3/8] backend/.env already exists"
fi

# 4. Database
echo "[4/8] Initializing database..."
cd backend
python3 -c "
import sys; sys.path.insert(0, '.')
from app.database.connection import init_db
init_db()
print('Database initialized')
"
cd ..

# 5. Model download
echo "[5/8] Checking SmolLM2-135M GGUF..."
MODEL_FILE="models/smollm2-135m.gguf"
if [ ! -f "$MODEL_FILE" ]; then
  echo "Downloading model (~105MB)..."
  curl -L -o "$MODEL_FILE" \
    "https://huggingface.co/bartowski/SmolLM2-135M-GGUF/resolve/main/SmolLM2-135M-Q4_K_M.gguf"
  echo "Model downloaded"
else
  echo "Model already exists"
fi

# 6. WhatsApp bridge
echo "[6/8] Setting up WhatsApp bridge..."
cd whatsapp-bridge
npm install
cd ..

# 7. Frontend build
echo "[7/8] Building frontend..."
cd frontend
npm install
npm run build
cd ..

# 8. Swap + systemd auto-start
echo "[8/8] Configuring swap and auto-start..."

# Swap (1024MB for Pi Zero 2 W)
if command -v dphys-swapfile &>/dev/null; then
  sudo dphys-swapfile swapoff 2>/dev/null || true
  sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
  sudo dphys-swapfile setup
  sudo dphys-swapfile swapon
  echo "Swap set to 1024MB"
fi

# Swappiness (avoid SD card wear)
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf > /dev/null
sudo sysctl -w vm.swappiness=10

# systemd service
SERVICE_FILE="/etc/systemd/system/productflow.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=ProductFlow AI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BASE_DIR
ExecStart=$BASE_DIR/scripts/start.sh
Restart=always
RestartSec=10
Environment=LD_LIBRARY_PATH=/usr/local/lib
Environment=NODE_OPTIONS=--max-old-space-size=128

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable productflow.service
echo "Auto-start enabled (productflow.service)"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start now:   sudo systemctl start productflow"
echo "Stop:        sudo systemctl stop productflow"
echo "Status:      sudo systemctl status productflow"
echo "Logs:        journalctl -u productflow -f"
echo "Dashboard:   http://$(hostname -I | awk '{print $1}'):8000"
