FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for confluent-kafka and PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install PyTorch CPU-only first (much smaller than full version)
RUN uv pip install --system torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

# Verify PyTorch installation
RUN python -c "import torch; print(f'PyTorch {torch.__version__} installed successfully')"

# Install dependencies (without building the package)
# These must match pyproject.toml dependencies + aws extra
RUN uv pip install --system \
    "confluent-kafka>=2.3.0" \
    "numpy>=1.24.0,<2.0.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "structlog>=24.1.0" \
    "scikit-learn>=1.4.0" \
    "joblib>=1.3.0" \
    "boto3>=1.34.0"

# Copy application code
COPY src/ src/
COPY scripts/ scripts/

# Create directories for models and data
RUN mkdir -p /app/models /app/data

# Set Python path so src/ is importable
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.config; print('OK')" || exit 1

# Run the application
CMD ["python", "-m", "src.main"]
