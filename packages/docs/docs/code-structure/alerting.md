# Alerting

The alerting service is a Python application that consumes anomalies, correlates them into incidents, and dispatches notifications through multiple channels.

## Overview

| Property | Value                                   |
| -------- | --------------------------------------- |
| Language | Python                                  |
| Location | `packages/alerting/`                    |
| Input    | Kafka topic `ics.anomalies`             |
| Output   | Kafka topic `ics.alerts`, notifications |
| API      | FastAPI on port 8084                    |
| State    | Redis                                   |

## What it does

1. **Consumes anomaly results** from the anomaly detection service
2. **Correlates anomalies into incidents** by source/destination/protocol
3. **Deduplicates alerts** to prevent notification fatigue
4. **Escalates priority** based on anomaly count and severity
5. **Dispatches notifications** to configured channels
6. **Provides REST API** for alert/incident management
7. **Stores state** in Redis for persistence

## Package structure

```
packages/alerting/
├── src/
│   ├── main.py                     # Entry point (Kafka + FastAPI)
│   ├── config.py                   # Pydantic settings
│   ├── kafka/
│   │   ├── consumer.py             # Anomaly consumer
│   │   └── producer.py             # Alert producer
│   ├── schemas/
│   │   ├── alert.py                # Alert schema
│   │   └── incident.py             # Incident schema
│   ├── correlation/
│   │   └── engine.py               # Groups anomalies into incidents
│   ├── deduplication/
│   │   └── tracker.py              # Suppresses duplicate alerts
│   ├── escalation/
│   │   └── manager.py              # Priority escalation rules
│   ├── notifications/
│   │   ├── base.py                 # NotificationChannel ABC
│   │   ├── console.py              # Console/log output
│   │   ├── webhook.py              # Generic webhook
│   │   ├── slack.py                # Slack integration
│   │   ├── splunk.py               # Splunk HEC
│   │   └── syslog.py               # Syslog with CEF format
│   ├── storage/
│   │   └── redis_store.py          # Redis operations
│   └── api/
│       └── routes.py               # FastAPI endpoints
├── tests/
├── requirements.txt
└── Dockerfile
```

## Core components

### Correlation Engine

Groups anomalies by `{src_ip}:{dst_ip}:{protocol}` within a time window (default: 5 minutes). Creates or updates incidents for each unique correlation key.

### Deduplication Tracker

Prevents notification spam by suppressing duplicate alerts with the same key within a suppression window (default: 60 seconds).

### Escalation Manager

Automatically escalates incident priority based on:

- Anomaly count thresholds (5→P3, 10→P2, 20→P1)
- Critical severity detections
- Multi-target attacks (single source hitting multiple destinations)

### Notification Manager

Dispatches alerts through enabled channels:

- **Console**: Logs alerts for debugging
- **Webhook**: Generic HTTP POST to any endpoint
- **Slack**: Rich formatted messages with severity colors
- **Splunk**: HTTP Event Collector (HEC) integration
- **Syslog**: RFC 3164 format with CEF for SIEM integration

## Alert schema

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "incident_id": "660e8400-e29b-41d4-a716-446655440001",
  "created_at": "2024-01-15T10:30:05Z",
  "severity": "high",
  "status": "open",
  "title": "Reconnaissance Detected",
  "description": "Unusual scanning pattern from 192.168.1.100",
  "source": {
    "src_ip": "192.168.1.100",
    "dst_ip": "192.168.1.10",
    "protocol": "modbus",
    "window_size": 60,
    "window_start": 1704067200
  },
  "anomaly_type": "reconnaissance",
  "ensemble_score": 0.85,
  "confidence": 0.92,
  "related_anomaly_count": 5,
  "feature_contributions": {
    "fc_unique_count": 0.25,
    "addr_range": 0.2
  }
}
```

## Incident schema

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "correlation_key": "192.168.1.100:192.168.1.10:modbus",
  "created_at": "2024-01-15T10:25:00Z",
  "updated_at": "2024-01-15T10:30:05Z",
  "status": "active",
  "priority": "P2",
  "anomaly_count": 12,
  "alert_ids": ["550e8400-..."],
  "max_ensemble_score": 0.85,
  "src_ips": ["192.168.1.100"],
  "dst_ips": ["192.168.1.10"],
  "anomaly_types": ["reconnaissance", "timing_anomaly"]
}
```

## API endpoints

| Method | Path                          | Description                            |
| ------ | ----------------------------- | -------------------------------------- |
| GET    | `/health`                     | Health check                           |
| GET    | `/metrics`                    | Prometheus metrics                     |
| GET    | `/alerts`                     | List alerts (filter: status, severity) |
| GET    | `/alerts/{id}`                | Get specific alert                     |
| POST   | `/alerts/{id}/acknowledge`    | Acknowledge alert                      |
| GET    | `/incidents`                  | List incidents                         |
| GET    | `/incidents/{id}`             | Get specific incident                  |
| POST   | `/incidents/{id}/acknowledge` | Acknowledge incident                   |

## Configuration

| Environment Variable         | Description      | Default                  |
| ---------------------------- | ---------------- | ------------------------ |
| `KAFKA_BOOTSTRAP_SERVERS`    | Kafka brokers    | `localhost:9092`         |
| `KAFKA_INPUT_TOPIC`          | Input topic      | `ics.anomalies`          |
| `KAFKA_OUTPUT_TOPIC`         | Output topic     | `ics.alerts`             |
| `REDIS_URL`                  | Redis connection | `redis://localhost:6379` |
| `CORRELATION_WINDOW_SECONDS` | Incident window  | `300`                    |
| `DEDUP_SUPPRESSION_SECONDS`  | Dedup window     | `60`                     |
| `ESCALATION_P3_THRESHOLD`    | Anomalies for P3 | `5`                      |
| `ESCALATION_P2_THRESHOLD`    | Anomalies for P2 | `10`                     |
| `ESCALATION_P1_THRESHOLD`    | Anomalies for P1 | `20`                     |
| `WEBHOOK_ENABLED`            | Enable webhook   | `false`                  |
| `WEBHOOK_URL`                | Webhook endpoint |                          |
| `SLACK_ENABLED`              | Enable Slack     | `false`                  |
| `SLACK_WEBHOOK_URL`          | Slack webhook    |                          |
| `SPLUNK_ENABLED`             | Enable Splunk    | `false`                  |
| `SPLUNK_HEC_URL`             | HEC endpoint     |                          |
| `SPLUNK_HEC_TOKEN`           | HEC token        |                          |
| `SYSLOG_ENABLED`             | Enable Syslog    | `false`                  |
| `SYSLOG_HOST`                | Syslog server    |                          |
| `SYSLOG_PORT`                | Syslog port      | `514`                    |
| `API_PORT`                   | API server port  | `8084`                   |

## How to run

### With Docker Compose

```bash
# Start the full stack
make dev-full

# View logs
docker compose logs -f alerting
```

### Local development

```bash
cd packages/alerting

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Run
python -m src.main

# Run tests
pytest tests/ -v
```

## Key dependencies

| Package           | Purpose                  |
| ----------------- | ------------------------ |
| `confluent-kafka` | Kafka consumer/producer  |
| `redis`           | State storage            |
| `fastapi`         | REST API                 |
| `uvicorn`         | ASGI server              |
| `httpx`           | HTTP client for webhooks |
| `pydantic`        | Data validation          |
| `structlog`       | Structured logging       |
