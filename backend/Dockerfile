FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/backend/.venv/bin:${PATH}"

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates xz-utils \
    && mkdir -p /tmp/ffmpeg \
    && curl -fsSL https://johnvansickle.com/ffmpeg/releases/ffmpeg-git-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp/ffmpeg --strip-components=1 \
    && install -m 0755 /tmp/ffmpeg/ffmpeg /usr/local/bin/ffmpeg \
    && install -m 0755 /tmp/ffmpeg/ffprobe /usr/local/bin/ffprobe \
    && rm -rf /tmp/ffmpeg /tmp/ffmpeg.tar.xz /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv yt-dlp

COPY backend /app/backend

RUN uv sync --frozen --no-dev
RUN uv run playwright install --with-deps chromium

RUN chmod +x /app/backend/scripts/run-api.sh /app/backend/scripts/run-worker.sh

EXPOSE 8000
