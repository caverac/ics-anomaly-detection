# Capture

The capture package is a Go service that captures raw network packets from a network interface and publishes them to Kafka for downstream processing.

## Overview

| Property | Value                            |
| -------- | -------------------------------- |
| Language | Go                               |
| Location | `packages/capture/`              |
| Input    | Network interface (e.g., `eth0`) |
| Output   | Kafka topic `ics.raw.packets`    |
| Port     | 8081 (metrics/health)            |

## What it does

1. **Captures raw network packets** from a network interface using [gopacket](https://github.com/google/gopacket) (Go wrapper for libpcap)

2. **Filters for ICS protocols** using BPF (Berkeley Packet Filter):
   - Port 502 → Modbus TCP
   - Port 20000 → DNP3
   - Port 4840 → OPC-UA

3. **Extracts packet metadata** including:
   - Timestamp
   - Source/destination IP addresses
   - Source/destination ports
   - Protocol (TCP/UDP)
   - Raw payload bytes

4. **Publishes to Kafka** in batches for efficiency (100 packets or 100ms, whichever comes first)

## Package structure

```
packages/capture/
├── cmd/capture/
│   └── main.go              # Entry point, wiring, graceful shutdown
├── internal/
│   ├── capture/
│   │   └── capture.go       # Packet capture using gopacket/pcap
│   ├── config/
│   │   └── config.go        # Configuration loading
│   └── kafka/
│       └── producer.go      # Kafka batch producer
├── pkg/types/
│   └── packet.go            # RawPacket struct definition
├── config.yaml              # Default configuration
├── Dockerfile
├── go.mod
└── Makefile
```

## Output schema

The capture service produces messages to `ics.raw.packets` with this structure:

```json
{
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "src_ip": "192.168.1.100",
  "dst_ip": "192.168.1.10",
  "src_port": 49152,
  "dst_port": 502,
  "protocol": "tcp",
  "payload_size": 12,
  "payload": "base64-encoded-bytes",
  "payload_hex": "000100000006010300000001"
}
```

## Configuration

The service can be configured via environment variables or `config.yaml`:

| Environment Variable  | Description                          | Default                                           |
| --------------------- | ------------------------------------ | ------------------------------------------------- |
| `CAPTURE_INTERFACE`   | Network interface to capture from    | `eth0`                                            |
| `CAPTURE_BPF_FILTER`  | BPF filter expression                | `tcp port 502 or tcp port 20000 or tcp port 4840` |
| `CAPTURE_PROMISCUOUS` | Enable promiscuous mode              | `true`                                            |
| `CAPTURE_SNAP_LEN`    | Maximum bytes to capture per packet  | `65535`                                           |
| `KAFKA_BROKERS`       | Kafka broker addresses               | `localhost:9092`                                  |
| `KAFKA_TOPIC`         | Output Kafka topic                   | `ics.raw.packets`                                 |
| `LOG_LEVEL`           | Log level (debug, info, warn, error) | `info`                                            |

## How to run

### Development (with Docker)

The capture service requires `NET_RAW` and `NET_ADMIN` capabilities for packet capture, and typically runs with `network_mode: host`:

```bash
# Build the capture service
make build-capture

# Run with the capture profile (requires root/sudo)
docker compose --profile capture up -d capture
```

### Local development

```bash
cd packages/capture

# Install dependencies
go mod download

# Build
go build -o bin/capture ./cmd/capture

# Run (requires root for packet capture)
sudo ./bin/capture -config config.yaml
```

### Testing

```bash
cd packages/capture

# Run tests
go test ./...

# Run with coverage
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

## Metrics

The service exposes Prometheus metrics on port 8081:

| Metric                            | Type    | Description                   |
| --------------------------------- | ------- | ----------------------------- |
| `capture_packets_total`           | counter | Total packets captured        |
| `capture_packets_published_total` | counter | Packets published to Kafka    |
| `capture_packets_dropped_total`   | counter | Packets dropped (buffer full) |
| `capture_bytes_total`             | counter | Total bytes captured          |
| `capture_errors_total`            | counter | Capture errors                |

## Health check

```bash
curl http://localhost:8081/health
# {"status":"healthy"}
```

## Note on the simulator

In the development environment, the **simulator bypasses the capture service** and generates synthetic ICS packets directly to `ics.raw.packets`. The capture service is designed for real network deployments where you need to capture actual traffic from PLCs, RTUs, and SCADA systems.
