#!/usr/bin/env bash
set -e

echo "=== ProductFlow AI Recovery ==="

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

# Activate virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Run recovery
echo "Running recovery sequence..."
cd backend
python3 -c "
import sys; sys.path.insert(0, '.')
from app.services.recovery_service import recovery_service
recovery_service.recover()
"
cd ..

echo "=== Recovery complete ==="
