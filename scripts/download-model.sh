#!/usr/bin/env bash
set -e

MODEL_DIR="$(cd "$(dirname "$0")/.." && pwd)/models"
MODEL_FILE="$MODEL_DIR/smollm2-135m.gguf"
URL="https://huggingface.co/bartowski/SmolLM2-135M-GGUF/resolve/main/SmolLM2-135M-Q4_K_M.gguf"

if [ -f "$MODEL_FILE" ]; then
  echo "Model already exists at $MODEL_FILE"
  exit 0
fi

mkdir -p "$MODEL_DIR"

echo "Downloading SmolLM2-135M GGUF (Q4_K_M)..."
echo "URL: $URL"
echo ""

if command -v curl &>/dev/null; then
  curl -L -o "$MODEL_FILE" "$URL"
elif command -v wget &>/dev/null; then
  wget -O "$MODEL_FILE" "$URL"
else
  echo "Need curl or wget"
  exit 1
fi

echo "Model downloaded to $MODEL_FILE"
echo "Size: $(du -h "$MODEL_FILE" | cut -f1)"
