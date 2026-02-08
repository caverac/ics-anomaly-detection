FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for confluent-kafka and PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install PyTorch CPU-only first (much smaller than full version)
# Pin to specific version for reproducibility
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

# Verify PyTorch installation
RUN python -c "import torch; print(f'PyTorch {torch.__version__} installed successfully')"

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

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
