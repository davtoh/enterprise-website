# ==============================================================================
# Multi-Stage Dockerfile for Enterprise Website (Django 5 + Channels 4)
# Builder stage compiles wheels and installs production dependencies.
# Runtime stage provides a minimal, secure, non-root execution container.
# ==============================================================================

# --- Stage 1: Build Dependencies ---
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install build-time packages required for compiling C extensions (psycopg2, Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    python3-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install production dependencies
COPY requirements/ /build/requirements/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /build/requirements/production.txt


# --- Stage 2: Minimal Runtime ---
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install minimal runtime dependencies (libpq for postgres, curl for healthchecks, gettext for translations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=enterprise_website.settings

# Create dedicated non-root application user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Create directories for static files and media with appropriate permissions
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Copy application source code
COPY --chown=appuser:appuser . /app/

# Ensure entrypoint script is executable
RUN chmod +x /app/docker-entrypoint.sh

# Compile translation message catalogs
RUN python manage.py compilemessages || true

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8000/ || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "enterprise_website.asgi:application"]
