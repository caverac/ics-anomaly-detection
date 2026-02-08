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
| Node.js | 22+ | Monorepo management, dashboard |
| Yarn | 4+ | Package manager |

### Optional (for local development)

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | ML services |
| Go | 1.21+ | Packet capture service |
| Rust | 1.75+ | Protocol parser |

## Quick Start with Docker

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/caverac/ics-anomaly-detection.git
cd ics-anomaly-detection

# Install dependencies
yarn install

# Start the full pipeline with dashboard
make dev-dashboard

# Access the dashboard
open http://localhost:3090
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start Kafka + Simulator + Parser + Feature Engine |
| `make dev-full` | Add Anomaly Detection |
| `make dev-alerting` | Add Alerting Service |
| `make dev-dashboard` | Add React Dashboard (full pipeline) |
| `make debug` | Add Kafka UI at localhost:8080 |
| `make monitoring` | Add Prometheus + Grafana |
| `make clean` | Remove all containers and volumes |

## Local Development Setup

For development with hot reloading on individual services:

### 1. Start Infrastructure

```bash
# Start Kafka and Redis
make up

# Verify services are healthy
docker compose ps
```

### 2. Run Services Locally

Each service can run independently. In separate terminals:

```bash
# Terminal 1: Simulator (generates test traffic)
cd packages/simulator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main

# Terminal 2: Parser (Rust)
cd packages/parser
cargo run

# Terminal 3: Feature Engine
cd packages/feature-engine
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main

# Terminal 4: Anomaly Detection
cd packages/anomaly-detection
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main

# Terminal 5: Alerting
cd packages/alerting
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main

# Terminal 6: Dashboard
cd packages/dashboard
npm install
npm run dev
```

## Configuration

### Environment Variables

Key environment variables (with defaults):

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Redis (for alerting service)
REDIS_URL=redis://localhost:6379

# Service ports
SIMULATOR_PORT=8083
ALERTING_PORT=8084
DASHBOARD_PORT=3090

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or 'console' for development
```

### Network Interface (Live Capture)

For live packet capture (advanced):

```bash
# List available interfaces
ip link show

# Set capture interface
export CAPTURE_INTERFACE=eth0
```

## Verify Installation

### 1. Check Services

```bash
docker compose ps
```

Expected output:
```
NAME              STATUS
ics-kafka         running (healthy)
ics-redis         running (healthy)
ics-simulator     running
ics-parser        running
ics-feature-engine running
```

### 2. Check Data Flow

```bash
# Watch raw packets
make kafka-consume-raw

# Watch parsed messages
make kafka-consume-parsed

# Watch features
make kafka-consume-features
```

### 3. Test Attack Simulation

```bash
# Start reconnaissance attack
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "reconnaissance"}'

# Check alerts (if alerting is running)
curl http://localhost:8084/alerts | jq
```

## Troubleshooting

### Kafka Connection Issues

```bash
# Check Kafka is running
docker compose logs kafka

# Verify topics created
make kafka-topics

# Restart with clean state
make clean && make up
```

### Python Import Errors

```bash
# Ensure you're in a virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Permission Denied (Packet Capture)

```bash
# Option 1: Run with sudo
sudo go run ./cmd/capture

# Option 2: Set capabilities (Linux)
sudo setcap cap_net_raw,cap_net_admin=eip ./capture
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8083

# Kill if needed
kill -9 <PID>
```
