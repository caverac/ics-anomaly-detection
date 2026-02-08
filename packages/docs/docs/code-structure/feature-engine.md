# Feature Engine

The feature engine is a Python service that aggregates parsed ICS messages into time windows and extracts statistical features for ML-based anomaly detection.

## Overview

| Property | Value                                                                   |
| -------- | ----------------------------------------------------------------------- |
| Language | Python                                                                  |
| Location | `packages/feature-engine/`                                              |
| Input    | Kafka topics `ics.parsed.modbus`, `ics.parsed.dnp3`, `ics.parsed.opcua` |
| Output   | Kafka topic `ics.features`                                              |

## What it does

1. **Consumes parsed messages** from protocol-specific topics
2. **Groups messages into time windows** by source IP, destination IP, protocol, and time bucket
3. **Extracts statistical features** when windows close:
   - Volume metrics (message count, bytes)
   - Timing metrics (inter-arrival times)
   - Protocol-specific metrics (function codes, addresses)
4. **Publishes feature vectors** for ML model consumption

## Package structure

```
packages/feature-engine/
├── src/
│   ├── main.py                 # Entry point, FeatureEngine class
│   ├── config.py               # Pydantic settings
│   ├── kafka/
│   │   ├── consumer.py         # Multi-topic consumer
│   │   └── producer.py         # Feature producer
│   ├── windows/
│   │   └── manager.py          # WindowManager, WindowBuffer
│   ├── extractors/
│   │   ├── base.py             # BaseExtractor with common features
│   │   ├── modbus.py           # Modbus-specific features
│   │   ├── dnp3.py             # DNP3-specific features
│   │   └── opcua.py            # OPC-UA-specific features
│   └── features/
│       └── vector.py           # FeatureVector Pydantic model
├── tests/
│   ├── test_extractors.py
│   ├── test_windows.py
│   └── test_vector.py
├── requirements.txt
└── Dockerfile
```

## Time windowing

Messages are grouped into fixed-size time windows:

```
Window Key = (src_ip, dst_ip, protocol, window_start)

Example:
  src_ip: 192.168.1.100
  dst_ip: 192.168.1.10
  protocol: modbus
  window_start: 1704067200 (epoch seconds, aligned to window size)
  window_size: 60 seconds
```

When a window closes (current time > window_start + window_size), features are extracted and the buffer is cleared.

## Feature categories

### Base features (all protocols)

| Feature         | Description                       |
| --------------- | --------------------------------- |
| `message_count` | Number of messages in window      |
| `bytes_total`   | Total payload bytes               |
| `bytes_mean`    | Mean payload size                 |
| `bytes_std`     | Std dev of payload size           |
| `bytes_min`     | Minimum payload size              |
| `bytes_max`     | Maximum payload size              |
| `iat_mean`      | Mean inter-arrival time (seconds) |
| `iat_std`       | Std dev of inter-arrival time     |
| `iat_min`       | Minimum inter-arrival time        |
| `iat_max`       | Maximum inter-arrival time        |
| `iat_median`    | Median inter-arrival time         |

### Modbus-specific features

| Feature                | Description                           |
| ---------------------- | ------------------------------------- |
| `fc_unique_count`      | Unique function codes                 |
| `fc_read_ratio`        | Ratio of read operations              |
| `fc_write_ratio`       | Ratio of write operations             |
| `fc_diagnostic_ratio`  | Ratio of diagnostic operations        |
| `fc_entropy`           | Entropy of function code distribution |
| `fc_most_common`       | Most common function code             |
| `fc_most_common_ratio` | Ratio of most common function code    |
| `unit_id_unique_count` | Unique unit IDs addressed             |
| `unit_id_entropy`      | Entropy of unit ID distribution       |
| `addr_unique_count`    | Unique register addresses             |
| `addr_mean`            | Mean address value                    |
| `addr_std`             | Std dev of addresses                  |
| `addr_min`             | Minimum address                       |
| `addr_max`             | Maximum address                       |
| `addr_range`           | Address range (max - min)             |
| `qty_mean`             | Mean quantity per request             |
| `qty_max`              | Maximum quantity                      |
| `exception_count`      | Number of exceptions                  |
| `exception_ratio`      | Ratio of exception responses          |
| `request_count`        | Number of requests                    |
| `response_count`       | Number of responses                   |
| `request_ratio`        | Ratio of requests to total            |

## Output schema

```json
{
  "_window_key": {
    "src_ip": "192.168.1.100",
    "dst_ip": "192.168.1.10",
    "protocol": "modbus",
    "window_size": 60,
    "window_start": 1704067200
  },
  "_extracted_at": "2024-01-15T10:30:00.123456Z",
  "protocol": "modbus",
  "window_size_seconds": 60,
  "message_count": 150,
  "bytes_total": 1800,
  "bytes_mean": 12.0,
  "bytes_std": 2.5,
  "iat_mean": 0.4,
  "iat_std": 0.1,
  "fc_unique_count": 3,
  "fc_read_ratio": 0.8,
  "fc_write_ratio": 0.15,
  "fc_entropy": 1.2,
  "addr_unique_count": 25,
  "exception_ratio": 0.0
}
```

## Configuration

| Environment Variable        | Description               | Default              |
| --------------------------- | ------------------------- | -------------------- |
| `KAFKA_BOOTSTRAP_SERVERS`   | Kafka broker addresses    | `localhost:9092`     |
| `KAFKA_GROUP_ID`            | Consumer group            | `ics-feature-engine` |
| `KAFKA_OUTPUT_TOPIC`        | Output topic              | `ics.features`       |
| `WINDOWS_WINDOW_SIZES`      | Window sizes (seconds)    | `[60]`               |
| `FEATURE_ENGINE_LOG_LEVEL`  | Log level                 | `INFO`               |
| `FEATURE_ENGINE_LOG_FORMAT` | Log format (json/console) | `json`               |

## How to run

### With Docker Compose

```bash
# Start with the development stack
make dev

# View logs
docker compose logs -f feature-engine
```

### Local development

```bash
cd packages/feature-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python -m src.main

# Run tests
pytest tests/ -v
```

## Key dependencies

| Package             | Purpose                   |
| ------------------- | ------------------------- |
| `confluent-kafka`   | Kafka consumer/producer   |
| `pydantic`          | Data validation, settings |
| `pydantic-settings` | Environment configuration |
| `numpy`             | Statistical computations  |
| `structlog`         | Structured logging        |
