---
sidebar_position: 2
---

# Installation

This guide covers setting up the development environment.

## Prerequisites

| Tool           | Version | Purpose                        |
| -------------- | ------- | ------------------------------ |
| Docker         | 24+     | Container runtime              |
| Docker Compose | 2.20+   | Multi-container orchestration  |
| Node.js        | 22+     | Monorepo management, dashboard |
| Yarn           | 4+      | Package manager                |

### Optional (for local development)

| Tool   | Version | Purpose                |
| ------ | ------- | ---------------------- |
| Python | 3.11    | ML services            |
| Go     | 1.23+   | Packet capture service |
| Rust   | 1.83+   | Protocol parser        |

### Using mise (Recommended)

We recommend using [mise](https://mise.jdx.dev/) to manage tool versions. It ensures everyone uses the same versions.

```bash
# Install mise
curl https://mise.run | sh

# Add to your shell (bash example)
echo 'eval "$(mise activate bash)"' >> ~/.bashrc
source ~/.bashrc

# Install all required tools
mise install

# Verify installation
mise current
```

This will install Node.js 22, Python 3.12, Go 1.23, and Rust 1.83 as specified in `mise.toml`.

## Quick Start with Docker

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/caverac/ics-anomaly-detection.git
cd ics-anomaly-detection

# Install Node.js dependencies
yarn install

# Start the full pipeline with dashboard
make dev-dashboard

# Access the dashboard
open http://localhost:3090

# Access the Swagger UI for the simulator
http://localhost:8083/docs

# Access the Swagger UI for the alerting service
http://localhost:8084/docs
```

## Tooling Philosophy

This project uses two tools with clear responsibilities:

| Tool       | Responsibility                                             |
| ---------- | ---------------------------------------------------------- |
| **`make`** | Docker/infrastructure operations, starting services        |
| **`yarn`** | Code quality (lint, format, typecheck), building artifacts |

### When to use `make`

```bash
make dev           # Start development environment
make dev-dashboard # Start full stack
make build         # Build Docker images
make kafka-topics  # Kafka utilities
make clean         # Cleanup
```

### When to use `yarn`

```bash
yarn lint          # Lint JS/TS code
yarn format        # Check formatting
yarn typecheck     # TypeScript checks
yarn test          # Run tests
yarn build         # Build docs + dashboard
yarn ci            # Full JS/TS CI pipeline
```

## Development Commands

### Starting Services

| Command              | Description                                       |
| -------------------- | ------------------------------------------------- |
| `make dev`           | Start Kafka + Simulator + Parser + Feature Engine |
| `make dev-full`      | Add Anomaly Detection                             |
| `make dev-alerting`  | Add Alerting Service                              |
| `make dev-dashboard` | Add React Dashboard (full pipeline)               |
| `make debug`         | Add Kafka UI at localhost:8080                    |
| `make monitoring`    | Add Prometheus + Grafana                          |
| `make status`        | Show status of all services                       |
| `make start`         | Start all services                                |
| `make all`           | Start all services                                |
| `make down`          | Stop all services                                 |
| `make clean`         | Remove all containers and volumes                 |

### Code Quality

| Command           | Description               |
| ----------------- | ------------------------- |
| `yarn lint`       | Lint JS/TS with ESLint    |
| `yarn lint:fix`   | Fix linting issues        |
| `yarn format`     | Check Prettier formatting |
| `yarn format:fix` | Fix formatting            |
| `yarn typecheck`  | Run TypeScript checks     |
| `yarn test`       | Run all tests             |
| `yarn build`      | Build docs + dashboard    |

### Development Servers

| Command              | Description                                 |
| -------------------- | ------------------------------------------- |
| `yarn dev:docs`      | Start docs dev server (localhost:3000)      |
| `yarn dev:dashboard` | Start dashboard dev server (localhost:5173) |

## Development Modes

There are two ways to run services:

### Option 1: Docker Mode (Recommended for most users)

Everything runs in containers. Simple and consistent.

```bash
make start    # Start all services in Docker
make down     # Stop all services
```

### Option 2: Local Mode (For debugging/development)

Run services locally with hot reloading. Useful when you need to debug or make frequent changes to a specific service.

:::warning Port Conflicts
You cannot run a service in Docker and locally at the same time - they use the same ports. Stop the Docker container before running locally.
:::

#### 1. Start Infrastructure Only

```bash
# Start only Kafka and Redis in Docker
make up

# Verify services are healthy
make status
```

#### 2. Run Services Locally

:::tip Using uv (Recommended)
We use [uv](https://docs.astral.sh/uv/) for fast Python dependency management. Install via mise or `curl -LsSf https://astral.sh/uv/install.sh | sh`
:::

:::info Kafka Connection
When running locally, use `localhost:9094` instead of `kafka:9092` (which is the Docker internal hostname).
:::

```bash
# Terminal 1: Simulator (generates test traffic)
cd packages/simulator
uv sync
KAFKA_BROKERS=localhost:9094 uv run python -m src.main

# Terminal 2: Parser (Rust)
cd packages/parser
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 cargo run

# Terminal 3: Feature Engine
cd packages/feature-engine
uv sync
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 uv run python -m src.main

# Terminal 4: Anomaly Detection
cd packages/anomaly-detection
uv sync
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 uv run python -m src.main

# Terminal 5: Alerting
cd packages/alerting
uv sync
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 uv run python -m src.main

# Terminal 6: Dashboard (with hot reload)
yarn dev:dashboard
```

### Option 3: Hybrid Mode (Mix of Docker and Local)

Run most services in Docker, but one locally for debugging:

```bash
# Start everything in Docker
make start

# Stop only the service you want to debug
docker stop ics-simulator

# Run that service locally
cd packages/simulator
KAFKA_BROKERS=localhost:9094 uv run python -m src.main
```

## Configuration

### Environment Variables

Key environment variables differ between Docker and local modes:

| Variable | Docker Mode | Local Mode |
|----------|-------------|------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | `localhost:9094` |
| `REDIS_URL` | `redis://redis:6379` | `redis://localhost:6379` |

Other common variables:

```bash
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
make status
```

Expected output:

```
=== Container Status ===
NAME                STATUS                  PORTS
ics-kafka           running (healthy)       0.0.0.0:9094->9094/tcp
ics-redis           running                 0.0.0.0:6379->6379/tcp
ics-simulator       running                 0.0.0.0:8083->8083/tcp
...

=== Service Health ===
  :8082 → 200
  :8083 → 200
  :8084 → 200
  :8085 → 200
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

## CI/CD

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`):

```bash
# Run locally (JS/TS only)
yarn ci

# Run full CI including Docker builds
yarn ci && make ci
```

The CI pipeline:

1. **Lint** - ESLint, Prettier, ruff, clippy, golangci-lint
2. **Typecheck** - TypeScript, mypy
3. **Test** - All unit tests
4. **Build** - Docs, dashboard, Docker images

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
# Reinstall dependencies with uv
uv sync

# Or with pip (legacy)
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
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
