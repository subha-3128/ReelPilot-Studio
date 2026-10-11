#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================="
echo " Starting ReelPilot Studio (Local Mac)"
echo "=========================================="

# Check ffmpeg & yt-dlp
if ! command -v ffmpeg &> /dev/null; then
  echo "Warning: ffmpeg not found in PATH."
fi
if ! command -v yt-dlp &> /dev/null; then
  echo "Warning: yt-dlp not found in PATH."
fi

# Ensure storage directories exist
mkdir -p storage/originals storage/voiceovers storage/derivatives storage/thumbnails storage/temp

cleanup() {
  echo ""
  echo "Shutting down ReelPilot Studio..."
  kill $(jobs -p) 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend FastAPI Server (FastAPI + Telegram Bot Worker)
echo "Starting backend at http://127.0.0.1:8000..."
cd "$DIR/backend"
PYTHONPATH=. "$DIR/backend/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend health check..."
for i in {1..15}; do
  if curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "Backend is healthy!"
    break
  fi
  sleep 1
done

# 2. Start Frontend Vite Dev Server
echo "Starting frontend at http://localhost:5173..."
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "ReelPilot Studio is running!"
echo "   Frontend:     http://localhost:5173"
echo "   Backend:      http://127.0.0.1:8000"
echo "   API Docs:     http://127.0.0.1:8000/docs"
echo "   Telegram Bot: Active (if TELEGRAM_BOT_TOKEN set in backend/.env)"
echo "Press Ctrl+C to stop servers."

wait
