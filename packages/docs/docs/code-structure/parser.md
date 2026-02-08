# Parser

The parser package is a Rust service that consumes raw packets from Kafka, parses ICS protocol payloads (Modbus, DNP3, OPC-UA), and produces structured messages for downstream analysis.

## Overview

| Property | Value |
|----------|-------|
| Language | Rust |
| Location | `packages/parser/` |
| Input | Kafka topic `ics.raw.packets` |
| Output | Kafka topics `ics.parsed.modbus`, `ics.parsed.dnp3`, `ics.parsed.opcua` |
| Port | 8082 (metrics/health) |

## What it does

1. **Consumes raw packets** from `ics.raw.packets` topic
2. **Decodes hex-encoded payloads** from the raw packet messages
3. **Parses protocol-specific structures** using the `nom` parser combinator library:
   - Modbus TCP: MBAP header + PDU parsing
   - DNP3: Frame header + transport/application layers
   - OPC-UA: Message header + service identification
4. **Produces structured messages** to protocol-specific topics

## Package structure

```
packages/parser/
├── src/
│   ├── main.rs              # Entry point, Kafka consumer/producer loop
│   ├── config/
│   │   └── mod.rs           # Configuration (env vars, TOML)
│   ├── kafka/
│   │   └── mod.rs           # Kafka consumer/producer wrappers
│   └── protocols/
│       ├── mod.rs           # Parser trait, message types
│       ├── modbus.rs        # Modbus TCP parser
│       ├── dnp3.rs          # DNP3 parser
│       └── opcua.rs         # OPC-UA parser
├── Cargo.toml
├── Dockerfile
└── Makefile
```

## Modbus parsing

The parser extracts detailed information from Modbus TCP messages:

### MBAP Header
- Transaction ID
- Protocol ID
- Length
- Unit ID

### Function codes supported

| Code | Function | Parsed Fields |
|------|----------|---------------|
| 0x01 | Read Coils | start_address, quantity |
| 0x02 | Read Discrete Inputs | start_address, quantity |
| 0x03 | Read Holding Registers | start_address, quantity, values |
| 0x04 | Read Input Registers | start_address, quantity, values |
| 0x05 | Write Single Coil | start_address, value |
| 0x06 | Write Single Register | start_address, value |
| 0x0F | Write Multiple Coils | start_address, quantity, byte_count |
| 0x10 | Write Multiple Registers | start_address, quantity, values |
| 0x2B | Device Identification | raw_data |

### Exception handling
- Detects exception responses (function code with 0x80 flag)
- Extracts exception codes

## Output schemas

### Modbus parsed message

```json
{
  "protocol": "modbus",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "src_ip": "192.168.1.100",
  "dst_ip": "192.168.1.10",
  "src_port": 49152,
  "dst_port": 502,
  "message": {
    "transaction_id": 1,
    "protocol_id": 0,
    "length": 6,
    "unit_id": 1,
    "function_code": 3,
    "function_name": "Read Holding Registers",
    "is_exception": false,
    "start_address": 0,
    "quantity": 10
  }
}
```

### DNP3 parsed message

```json
{
  "protocol": "dnp3",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "src_ip": "192.168.1.100",
  "dst_ip": "192.168.1.10",
  "src_port": 49152,
  "dst_port": 20000,
  "message": {
    "start_bytes": 1380,
    "length": 5,
    "control": 192,
    "destination": 1,
    "source": 2,
    "is_master": true,
    "function_code": 4,
    "function_name": "Unconfirmed User Data"
  }
}
```

### OPC-UA parsed message

```json
{
  "protocol": "opcua",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "src_ip": "192.168.1.100",
  "dst_ip": "192.168.1.10",
  "src_port": 49152,
  "dst_port": 4840,
  "message": {
    "message_type": "Hello",
    "message_type_code": [72, 69, 76],
    "is_final": true,
    "message_size": 28,
    "protocol_version": 0,
    "receive_buffer_size": 65536,
    "send_buffer_size": 65536
  }
}
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `KAFKA_BROKERS` | Kafka broker addresses | `localhost:9092` |
| `KAFKA_GROUP_ID` | Consumer group ID | `ics-parser` |
| `KAFKA_INPUT_TOPIC` | Input topic | `ics.raw.packets` |
| `KAFKA_CLIENT_ID` | Client identifier | `ics-parser` |
| `METRICS_PORT` | Health/metrics port | `8082` |
| `RUST_LOG` | Log level | `info` |

## How to run

### With Docker Compose

```bash
# Build and start
docker compose up -d parser

# View logs
docker compose logs -f parser
```

### Local development

```bash
cd packages/parser

# Build
cargo build --release

# Run (requires Kafka)
KAFKA_BROKERS=localhost:9094 cargo run

# Run tests
cargo test

# Run with coverage
cargo tarpaulin --out Html
```

### Linting

```bash
# Format check
cargo fmt --check

# Clippy
cargo clippy -- -D warnings
```

## Metrics

The service exposes Prometheus metrics on port 8082:

```bash
curl http://localhost:8082/metrics
```

## Health check

```bash
curl http://localhost:8082/health
# OK
```

## Key dependencies

| Crate | Purpose |
|-------|---------|
| `rdkafka` | Kafka client (librdkafka wrapper) |
| `nom` | Parser combinators for binary protocols |
| `tokio` | Async runtime |
| `axum` | HTTP server for metrics |
| `serde` | Serialization |
| `tracing` | Structured logging |

## Testing

The parser includes comprehensive unit tests for each protocol:

```bash
# Run all tests
cargo test

# Run specific protocol tests
cargo test modbus
cargo test dnp3
cargo test opcua

# Run with output
cargo test -- --nocapture
```
