#!/usr/bin/env bash
# ProductFlow AI — Oracle Cloud (Ubuntu 22.04/24.04) Deployment
# Usage: sudo bash setup.sh
set -euo pipefail

APP_DIR="/opt/productflow"
REPO_URL="https://github.com/JerryInd/ProductFlow.git"
BRANCH="main"
SWAP_MB=1024
GROQ_API_KEY="${GROQ_API_KEY:-}"

echo "========================================="
echo "  ProductFlow AI — Oracle Cloud Setup"
echo "========================================="

# --- 1. System packages ---
echo "[1/8] Installing system packages..."
apt-get update -qq
apt-get install -y -qq curl git build-essential python3 python3-venv python3-pip nodejs npm sqlite3

# Ensure Node 20+
NODE_VER=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VER" -lt 20 ]; then
  echo "Node.js too old ($NODE_VER), installing v20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

echo "  Python: $(python3 --version)"
echo "  Node:   $(node -v)"
echo "  npm:    $(npm -v)"

# --- 2. Swap ---
echo "[2/8] Setting up ${SWAP_MB}MB swap..."
if [ ! -f /swapfile ]; then
  fallocate -l ${SWAP_MB}M /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "vm.swappiness=10" >> /etc/sysctl.conf
  sysctl -p
  echo "  Swap created."
else
  echo "  Swap already exists."
fi

# --- 3. Clone repo ---
echo "[3/8] Cloning repository..."
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR"
  git pull origin "$BRANCH" --quiet
else
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi
echo "  Repo at $APP_DIR ($(git rev-parse --short HEAD))"

# --- 4. Python venv ---
echo "[4/8] Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt
echo "  $(python --version) with $(pip list --format=columns | wc -l) packages"

# --- 5. Node dependencies ---
echo "[5/8] Installing WhatsApp bridge dependencies..."
cd whatsapp-bridge
npm install --production --silent
cd ..
echo "  Bridge ready."

# --- 6. Build frontend ---
echo "[6/8] Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..
echo "  Frontend built to frontend/build/"

# --- 7. Initialize database ---
echo "[7/8] Initializing database..."
mkdir -p database data media-cache sessions logs backups
if [ ! -f database/productflow.db ]; then
  sqlite3 database/productflow.db < database/schema.sql
  echo "  Database created."
else
  echo "  Database already exists."
fi

# --- 8. Environment file ---
echo "[8/8] Configuring environment..."
if [ ! -f backend/.env ]; then
  cat > backend/.env <<EOF
GROQ_API_KEY=${GROQ_API_KEY}
GROQ_MODEL=llama-3.3-70b-versatile
EOF
  echo "  backend/.env created — edit to set GROQ_API_KEY"
else
  echo "  backend/.env already exists."
fi

# --- Create systemd service ---
echo "Creating systemd service..."
cat > /etc/systemd/system/productflow.service <<EOF
[Unit]
Description=ProductFlow AI
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/scripts/start.sh
Restart=on-failure
RestartSec=10
Environment=NODE_OPTIONS=--dns-result-order=ipv4first
EnvironmentFile=-$APP_DIR/backend/.env

[Install]
WantedBy=multi-user.target
EOF

chmod +x scripts/start.sh
systemctl daemon-reload
systemctl enable productflow
echo "  Service installed."

# --- Firewall ---
echo "Configuring firewall..."
if command -v ufw &>/dev/null; then
  ufw allow 8000/tcp 2>/dev/null || true
  echo "  Port 8000 opened."
fi

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "  Start:  sudo systemctl start productflow"
echo "  Status: sudo systemctl status productflow"
echo "  Logs:   journalctl -u productflow -f"
echo "  Stop:   sudo systemctl stop productflow"
echo ""
echo "  Dashboard: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "  NEXT STEPS:"
echo "  1. Edit GROQ_API_KEY: sudo nano /opt/productflow/backend/.env"
echo "  2. Start: sudo systemctl start productflow"
echo "  3. Scan QR code in terminal to link WhatsApp"
echo ""
