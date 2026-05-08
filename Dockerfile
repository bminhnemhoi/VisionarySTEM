# VisionarySTEM Backend — production-ready container
# Build:  docker build -t visionarystem:latest .
# Run:    docker run -p 8000:8000 --env-file .env visionarystem:latest

FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt \
    && pip install --user --no-cache-dir 'sqlalchemy[asyncio]>=2.0' asyncpg alembic 'python-jose[cryptography]' 'passlib[bcrypt]' boto3 redis

# ---- Final image ----
FROM python:3.12-slim

LABEL org.opencontainers.image.title="VisionarySTEM API"
LABEL org.opencontainers.image.description="Multimodal AI for visually impaired STEM students"
LABEL org.opencontainers.image.licenses="MIT"

# Non-root user
RUN useradd -u 1000 -m vs

# Install runtime libs (PyMuPDF needs minimal deps when binary wheel)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.local /home/vs/.local
COPY --chown=vs:vs src/ ./src/
COPY --chown=vs:vs scripts/ ./scripts/
COPY --chown=vs:vs pyproject.toml requirements.txt ./
# Sample data — required by /api/v1/mock/analyze + library endpoints
COPY --chown=vs:vs tests/sample_data/ ./tests/sample_data/

# Pre-create runtime dirs needed by config.py mkdir at import time.
# IMPORTANT: chown -R vs:vs /app so non-root user can mkdir/write.
RUN mkdir -p /app/uploads /app/output/tts_cache /app/output/gemini_tts_cache \
    && chown -R vs:vs /app

ENV PATH=/home/vs/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER vs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
