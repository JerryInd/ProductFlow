#!/usr/bin/env bash
set -e

echo "=== ProductFlow AI Recovery ==="

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

# Activate virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
fi

# Run recovery
echo "Running recovery sequence..."
cd backend
python -c "
from app.services.recovery_service import recovery_service
recovery_service.recover()
"
cd ..

echo "=== Recovery complete ==="
