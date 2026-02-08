FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for confluent-kafka and PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml .

# Install PyTorch CPU-only first (much smaller than full version)
RUN uv pip install --system torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

# Verify PyTorch installation
RUN python -c "import torch; print(f'PyTorch {torch.__version__} installed successfully')"

# Install remaining dependencies (including aws extras for S3 support)
RUN uv pip install --system .[aws]

# Copy application code
COPY src/ src/
COPY scripts/ scripts/

# Create directories for models and data
RUN mkdir -p /app/models /app/data

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.config; print('OK')" || exit 1

# Run the application
CMD ["python", "-m", "src.main"]
