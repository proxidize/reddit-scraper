FROM python:3.11-slim as builder

ARG BUILD_DATE
ARG VERSION=0.1.0

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY README.md ./
COPY reddit_scraper/ ./reddit_scraper/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -e .

FROM python:3.11-slim as production

LABEL maintainer="Reddit Scraper Team" \
      version="0.1.0" \
      description="A comprehensive Reddit scraper with proxy rotation and captcha solving"

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd -r scraper && useradd -r -g scraper scraper

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY reddit_scraper/ ./reddit_scraper/
COPY pyproject.toml ./
COPY README.md ./
COPY config.example.json ./

RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/data /app/config && \
    chown -R scraper:scraper /app

USER scraper

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import reddit_scraper; print('OK')" || exit 1

ENTRYPOINT ["reddit-scraper"]
CMD ["--help"]

VOLUME ["/app/config", "/app/data"]