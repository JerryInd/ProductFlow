#!/usr/bin/env bash
set -e

echo "=== ProductFlow AI Starting ==="

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

# Activate virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Fallback: use full path if venv activation didn't set PATH
if ! command -v uvicorn &>/dev/null && [ -f ".venv/bin/uvicorn" ]; then
  export PATH="$BASE_DIR/.venv/bin:$PATH"
fi

# llama.cpp needs this
export LD_LIBRARY_PATH=/usr/local/lib:${LD_LIBRARY_PATH:-}
export PATH=/usr/local/bin:${PATH:-}

# Node.js memory limit for bridge
export NODE_OPTIONS="${NODE_OPTIONS:-} --max-old-space-size=128"

# Start backend with single worker and no access logs
echo "Starting backend on port ${API_PORT:-8000}..."
cd backend
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${API_PORT:-8000}" \
  --workers 1 \
  --no-access-log &
BACKEND_PID=$!
cd ..

# Start WhatsApp bridge
echo "Starting WhatsApp bridge..."
cd whatsapp-bridge
node bridge.js &
BRIDGE_PID=$!
cd ..

# Trap to clean up on exit
cleanup() {
  echo "Shutting down..."
  kill $BRIDGE_PID 2>/dev/null
  kill $BACKEND_PID 2>/dev/null
  wait $BACKEND_PID 2>/dev/null
  wait $BRIDGE_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "Backend PID: $BACKEND_PID"
echo "WhatsApp PID: $BRIDGE_PID"
echo "Dashboard: http://localhost:${API_PORT:-8000}"
echo "Press Ctrl+C to stop."

wait $BACKEND_PID $BRIDGE_PID
