#!/usr/bin/env bash
# Health check for ProductFlow AI — restarts service if backend or bridge is down

SERVICE="productflow"
BACKEND_URL="http://localhost:8000/api/health"
BRIDGE_URL="http://localhost:8001/groups"
LOG_TAG="[HealthCheck]"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_TAG $1"; }

# Check backend
BACKEND_OK=false
BACKEND_RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BACKEND_URL" 2>/dev/null)
if [ "$BACKEND_RESP" = "200" ]; then
  BACKEND_OK=true
fi

# Check bridge
BRIDGE_OK=false
BRIDGE_RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BRIDGE_URL" 2>/dev/null)
if [ "$BRIDGE_RESP" = "200" ]; then
  BRIDGE_OK=true
fi

# Check if node/python processes are alive
NODE_ALIVE=$(pgrep -f "node bridge.js" >/dev/null 2>&1 && echo "yes" || echo "no")
PYTHON_ALIVE=$(pgrep -f "uvicorn app.main" >/dev/null 2>&1 && echo "yes" || echo "no")

# Decision
if [ "$BACKEND_OK" = true ] && [ "$BRIDGE_OK" = true ]; then
  log "OK — backend:200 bridge:200 node:$NODE_ALIVE python:$PYTHON_ALIVE"
  exit 0
fi

# Something is wrong — log and restart
log "FAIL — backend:${BACKEND_RESP} bridge:${BRIDGE_RESP} node:$NODE_ALIVE python:$PYTHON_ALIVE"
log "Restarting $SERVICE..."
systemctl restart "$SERVICE"
log "Restart sent."
