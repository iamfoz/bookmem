FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Basic runtime tools. Keep this deliberately small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE AUTHORS.md NOTICE CHANGELOG.md ./
COPY bookmem ./bookmem
COPY config ./config

RUN pip install --upgrade pip \
    && pip install -e .

# Runtime data is mounted by docker-compose.
RUN mkdir -p /app/data/books \
    /app/data/raw-books \
    /app/data/lancedb \
    /app/data/manifests \
    /app/data/review \
    /app/data/summaries \
    /app/data/notes \
    /app/exports

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=5)" || exit 1

CMD ["bookmem", "serve", "--host", "0.0.0.0", "--port", "8765"]
