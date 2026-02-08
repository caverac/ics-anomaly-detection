# Simulator

The simulator package is a Python service that generates synthetic ICS traffic for testing the anomaly detection pipeline without requiring real industrial equipment.

## Overview

| Property | Value                         |
| -------- | ----------------------------- |
| Language | Python                        |
| Location | `packages/simulator/`         |
| Input    | API commands                  |
| Output   | Kafka topic `ics.raw.packets` |
| Port     | 8083 (API + metrics)          |

## What it does

1. **Generates realistic Modbus TCP traffic** with proper protocol structure:
   - MBAP (Modbus Application Protocol) headers
   - Function codes with realistic distribution
   - Valid register addresses and values

2. **Simulates an ICS network** with:
   - 4 PLCs/RTUs at `192.168.1.10-12`, `192.168.1.20`
   - 2 HMI stations at `192.168.1.100-101`
   - Configurable message rate (default: 100 msg/s)

3. **Supports attack simulation modes** for testing detection:
   - `reconnaissance` - Device identification scanning
   - `write_attack` - Unusual write operations
   - `replay` - Message replay patterns (planned)
   - `dos` - Denial of service patterns (planned)

4. **Provides a REST API** for runtime control

## Package structure

```
packages/simulator/
├── src/
│   └── main.py         # All-in-one: config, generators, API
├── requirements.txt    # Dependencies
└── Dockerfile
```

## Output schema

Messages published to `ics.raw.packets`:

```json
{
  "timestamp": "2024-01-15T10:30:00.123456+00:00",
  "src_ip": "192.168.1.100",
  "dst_ip": "192.168.1.10",
  "src_port": 52341,
  "dst_port": 502,
  "protocol": "tcp",
  "ics_protocol": "modbus",
  "payload_size": 12,
  "payload_hex": "000100000006010300000001"
}
```

## Simulated devices

### PLCs/RTUs (destinations)

| IP           | Unit ID | Type | Register Range |
| ------------ | ------- | ---- | -------------- |
| 192.168.1.10 | 1       | PLC  | 0-99           |
| 192.168.1.11 | 2       | PLC  | 100-199        |
| 192.168.1.12 | 3       | PLC  | 200-299        |
| 192.168.1.20 | 1       | RTU  | 0-49           |

### HMI stations (sources)

| IP            | Type |
| ------------- | ---- |
| 192.168.1.100 | HMI  |
| 192.168.1.101 | HMI  |

## Modbus function codes

The simulator generates traffic with realistic function code distribution:

| Code | Function                 | Probability |
| ---- | ------------------------ | ----------- |
| 0x03 | Read Holding Registers   | 60%         |
| 0x04 | Read Input Registers     | 20%         |
| 0x06 | Write Single Register    | 10%         |
| 0x10 | Write Multiple Registers | 5%          |
| 0x01 | Read Coils               | 3%          |
| 0x05 | Write Single Coil        | 2%          |

## API endpoints

### Health & status

```bash
# Health check
curl http://localhost:8083/health
# {"status": "healthy", "running": true}

# Current status
curl http://localhost:8083/status
# {"running": true, "rate": 100, "protocol": "modbus", "attack_mode": null}

# Prometheus metrics
curl http://localhost:8083/metrics
```

### Configuration

```bash
# Change message rate
curl -X POST http://localhost:8083/config \
  -H "Content-Type: application/json" \
  -d '{"rate": 200}'

# Change protocol (modbus, mixed)
curl -X POST http://localhost:8083/config \
  -H "Content-Type: application/json" \
  -d '{"protocol": "mixed"}'
```

### Attack simulation

```bash
# Start reconnaissance attack
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "reconnaissance"}'

# Start write attack
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "write_attack"}'

# Stop attack
curl -X POST http://localhost:8083/attack/stop
```

## Configuration

| Environment Variable | Description            | Default           |
| -------------------- | ---------------------- | ----------------- |
| `KAFKA_BROKERS`      | Kafka broker addresses | `localhost:9092`  |
| `KAFKA_TOPIC`        | Output Kafka topic     | `ics.raw.packets` |
| `SIMULATOR_RATE`     | Messages per second    | `100`             |
| `SIMULATOR_PROTOCOL` | Protocol to simulate   | `modbus`          |
| `METRICS_PORT`       | API/metrics port       | `8083`            |

## How to run

### With Docker Compose (recommended)

```bash
# Start infrastructure + simulator
make dev

# Or with the simulator profile explicitly
docker compose --profile simulator up -d
```

### Local development

```bash
cd packages/simulator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run (requires Kafka running)
python src/main.py
```

## Metrics

| Metric                              | Type      | Description                 |
| ----------------------------------- | --------- | --------------------------- |
| `simulator_messages_sent_total`     | counter   | Messages sent (by protocol) |
| `simulator_errors_total`            | counter   | Send errors                 |
| `simulator_message_latency_seconds` | histogram | Message generation time     |

## Testing the pipeline

```bash
# 1. Start the development environment
make dev

# 2. Check simulator status
curl http://localhost:8083/status

# 3. View generated messages in Kafka
make kafka-consume-raw

# 4. Start an attack to generate anomalies
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "reconnaissance"}'

# 5. View detected anomalies (if full pipeline is running)
make kafka-consume-anomalies

# 6. Stop the attack
curl -X POST http://localhost:8083/attack/stop
```
