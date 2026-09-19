# =============================================================================
# Stage 1: Build & Dependencies
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

# Install dependencies into /install
RUN pip install --upgrade pip && \
    pip install --prefix=/install . && \
    pip install --prefix=/install spacy && \
    python -m spacy download en_core_web_sm --target=/install/lib/python3.12/site-packages

# =============================================================================
# Stage 2: Production Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -g 10001 vikas && \
    useradd -u 10001 -g vikas -s /bin/bash -m vikasuser

# Copy application source code
COPY --chown=vikasuser:vikas alembic.ini .
COPY --chown=vikasuser:vikas alembic/ ./alembic
COPY --chown=vikasuser:vikas app/ ./app
COPY --chown=vikasuser:vikas scripts/ ./scripts

USER vikasuser

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ENVIRONMENT=production

EXPOSE 8000

# Native Docker Healthcheck querying active DB-connected endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Automatically execute database migrations before starting server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]

