---
sidebar_position: 3
---

# Quickstart

Get the system running and detecting anomalies in 5 minutes.

## Start the System

```bash
# Start development environment
make dev
```

This starts:
- **Kafka** - Message broker
- **Redis** - Caching layer
- **Simulator** - Generates test Modbus traffic
- **Parser** - Parses ICS protocols

See [Docker Setup](/getting-started/docker-setup) for detailed configuration options.

## Verify Services

Check that all services are running:

```bash
docker compose ps
```

Expected output:
```
NAME            STATUS
ics-kafka       running (healthy)
ics-redis       running (healthy)
ics-simulator   running
ics-parser      running
```

## View Traffic

Watch messages flow through the system:

```bash
# Terminal 1: Raw packets from simulator
make kafka-consume-raw

# Terminal 2: Parsed Modbus messages
make kafka-consume-parsed
```

## Trigger an Anomaly

Inject a reconnaissance attack to test detection:

```bash
# Start reconnaissance attack (device scanning)
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "reconnaissance"}'

# Watch raw traffic for Device ID requests (FC 43)
make kafka-consume-raw

# Stop the attack
curl -X POST http://localhost:8083/attack/stop
```

**Available attack modes:**

| Mode | Description |
|------|-------------|
| `reconnaissance` | Device enumeration using Modbus FC 43 |
| `write_attack` | Unauthorized write commands |

## Explore the Simulator API

```bash
# Check simulator status
curl http://localhost:8083/status | jq

# Get health
curl http://localhost:8083/health

# View metrics
curl http://localhost:8083/metrics
```

## Configure Traffic

```bash
# Increase traffic rate to 500 msg/sec
curl -X POST http://localhost:8083/config \
  -H "Content-Type: application/json" \
  -d '{"rate": 500}'

# Check status
curl http://localhost:8083/status
```

## Add Monitoring

Start Prometheus and Grafana for observability:

```bash
make monitoring
```

Access:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## Next Steps

Now that you have the system running:

1. **[Docker Setup](/getting-started/docker-setup)** - Detailed Docker Compose configuration
2. **[Understand the Architecture](/architecture/system-context)** - Deep dive into system design
3. **[Explore Attack Scenarios](/simulation/attack-scenarios)** - Test different attack types
4. **[Data Flow](/architecture/data-flow)** - How messages flow through the system
