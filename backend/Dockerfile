FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/backend/.venv/bin:${PATH}"

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv yt-dlp

COPY backend /app/backend

RUN uv sync --frozen --no-dev

RUN chmod +x /app/backend/scripts/run-api.sh /app/backend/scripts/run-worker.sh

EXPOSE 8000
