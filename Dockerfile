# ReelPilot Studio — Zero-Budget Cloud Production Dockerfile
# Optimized for Oracle Cloud Always Free (x86_64 & aarch64 ARM Ampere)

FROM python:3.12-slim-bookworm

# Prevent Python from writing .pyc and enable unbuffered output for real-time logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install system dependencies: ffmpeg, ffprobe, curl, ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application source
COPY backend /app/backend

# Create storage persistent volume directories
RUN mkdir -p /app/storage/originals \
             /app/storage/voiceovers \
             /app/storage/derivatives \
             /app/storage/thumbnails \
             /app/storage/temp

# Expose internal API port
EXPOSE 8000

# Health check to ensure service vitality
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/api/health || exit 1

# Start ReelPilot FastAPI + Telegram Bot + Scheduler Worker
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
