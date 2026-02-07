---
sidebar_position: 2
---

# Installation

This guide covers setting up the development environment.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Node.js | 22+ | TypeScript services |
| Python | 3.11+ | ML services |
| Go | 1.21+ | Packet capture service |
| Rust | 1.75+ | Protocol parser |

## Quick Start with Docker

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/caverac/ics-anomaly-detection.git
cd ics-anomaly-detection

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Access the dashboard
open http://localhost:3000
```

## Development Setup

For local development with hot reloading:

### 1. Install Dependencies

```bash
# Install Node.js dependencies (monorepo)
yarn install

# Install Python dependencies
cd packages/ml
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Go dependencies
cd packages/capture
go mod download

# Install Rust dependencies
cd packages/parser
cargo build
```

### 2. Start Infrastructure

```bash
# Start only infrastructure services
docker compose up -d kafka timescaledb postgres redis

# Verify services are healthy
docker compose ps
```

### 3. Start Services

In separate terminals:

```bash
# Terminal 1: Packet capture (requires sudo for raw sockets)
cd packages/capture
sudo go run main.go

# Terminal 2: Protocol parser
cd packages/parser
cargo run

# Terminal 3: Feature engine
cd packages/ml
python -m feature_engine.main

# Terminal 4: Inference service
cd packages/ml
python -m inference.main

# Terminal 5: API
cd packages/api
yarn dev

# Terminal 6: Dashboard
cd packages/dashboard
yarn dev
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ics_anomaly
POSTGRES_USER=ics
POSTGRES_PASSWORD=ics_password

# TimescaleDB
TIMESCALE_HOST=localhost
TIMESCALE_PORT=5433
TIMESCALE_DB=ics_timeseries
TIMESCALE_USER=ics
TIMESCALE_PASSWORD=ics_password

# Redis
REDIS_URL=redis://localhost:6379

# ML
MODEL_REGISTRY_PATH=./models
INFERENCE_BATCH_SIZE=100
ANOMALY_THRESHOLD=0.7

# API
API_PORT=8080
JWT_SECRET=your-secret-key
```

### Network Interface

For live capture, specify the network interface:

```bash
# List available interfaces
ip link show

# Set capture interface
export CAPTURE_INTERFACE=eth0
```

## Verify Installation

Run the health check:

```bash
# Check all services
./scripts/healthcheck.sh

# Expected output:
# ✓ Kafka: healthy
# ✓ PostgreSQL: healthy
# ✓ TimescaleDB: healthy
# ✓ Redis: healthy
# ✓ Capture: healthy
# ✓ Parser: healthy
# ✓ Feature Engine: healthy
# ✓ Inference: healthy
# ✓ API: healthy
# ✓ Dashboard: healthy
```

## Troubleshooting

### Kafka Connection Issues

```bash
# Check Kafka is running
docker compose logs kafka

# Verify topics created
docker compose exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Permission Denied (Packet Capture)

```bash
# Option 1: Run with sudo
sudo go run main.go

# Option 2: Set capabilities (Linux)
sudo setcap cap_net_raw,cap_net_admin=eip ./capture
```

### GPU Not Detected (ML Inference)

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# If false, install CUDA toolkit or use CPU mode
export INFERENCE_DEVICE=cpu
```
