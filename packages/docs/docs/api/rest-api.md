---
sidebar_position: 1
---

# REST API

API reference for the ICS Anomaly Detection Engine.

## Base URL

```
http://localhost:8080/api/v1
```

## Authentication

All endpoints require authentication via JWT or API key.

```bash
# JWT Bearer token
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/v1/alerts

# API Key
curl -H "X-API-Key: <key>" http://localhost:8080/api/v1/alerts
```

## Endpoints

### Alerts

#### List Alerts

```http
GET /api/v1/alerts
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | all | Filter by status: `open`, `acknowledged`, `resolved` |
| `severity` | string | all | Filter: `critical`, `high`, `medium`, `low` |
| `type` | string | all | Filter by anomaly type |
| `start_time` | ISO8601 | -24h | Start of time range |
| `end_time` | ISO8601 | now | End of time range |
| `limit` | int | 50 | Max results (1-1000) |
| `offset` | int | 0 | Pagination offset |

**Response:**

```json
{
  "alerts": [
    {
      "id": "alert-123",
      "timestamp": "2024-01-15T10:30:00Z",
      "severity": "high",
      "type": "RECONNAISSANCE",
      "status": "open",
      "source_ip": "192.168.1.50",
      "dest_ip": "192.168.1.10",
      "anomaly_score": 0.89,
      "description": "Device scanning detected from 192.168.1.50",
      "mitre_technique": "T0846"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

#### Get Alert Details

```http
GET /api/v1/alerts/:id
```

**Response:**

```json
{
  "id": "alert-123",
  "timestamp": "2024-01-15T10:30:00Z",
  "severity": "high",
  "type": "RECONNAISSANCE",
  "status": "open",
  "source_ip": "192.168.1.50",
  "dest_ip": "192.168.1.10",
  "anomaly_score": 0.89,
  "model_scores": {
    "isolation_forest": 0.92,
    "lstm_autoencoder": 0.85,
    "one_class_svm": 0.88
  },
  "features": {
    "unique_destinations_5m": 45,
    "scan_score_15m": 0.91,
    "msg_count_1m": 2500
  },
  "related_alerts": ["alert-120", "alert-121", "alert-122"],
  "mitre_attack": {
    "technique": "T0846",
    "name": "Remote System Discovery",
    "tactic": "Discovery"
  },
  "timeline": [
    {"time": "2024-01-15T10:30:00Z", "event": "created"},
    {"time": "2024-01-15T10:35:00Z", "event": "enriched"}
  ]
}
```

#### Update Alert

```http
PATCH /api/v1/alerts/:id
```

**Request Body:**

```json
{
  "status": "acknowledged",
  "assignee": "analyst@example.com",
  "notes": "Investigating - appears to be maintenance scan"
}
```

### Devices

#### List Devices

```http
GET /api/v1/devices
```

**Response:**

```json
{
  "devices": [
    {
      "ip": "192.168.1.10",
      "first_seen": "2024-01-01T00:00:00Z",
      "last_seen": "2024-01-15T10:30:00Z",
      "protocol": "modbus",
      "device_type": "plc",
      "unit_ids": [1, 2],
      "baseline_status": "established",
      "alert_count_24h": 0
    }
  ],
  "total": 25
}
```

### Models

#### Get Model Status

```http
GET /api/v1/models
```

**Response:**

```json
{
  "models": [
    {
      "name": "isolation_forest",
      "version": "1.2.3",
      "stage": "production",
      "loaded_at": "2024-01-15T00:00:00Z",
      "metrics": {
        "inference_latency_p99_ms": 5.2,
        "inferences_total": 1250000
      }
    },
    {
      "name": "lstm_autoencoder",
      "version": "2.0.1",
      "stage": "production",
      "loaded_at": "2024-01-15T00:00:00Z",
      "metrics": {
        "inference_latency_p99_ms": 18.5,
        "inferences_total": 1250000
      }
    }
  ]
}
```

#### Reload Models

```http
POST /api/v1/models/reload
```

Trigger hot-reload of models from registry.

### Metrics

#### System Metrics

```http
GET /api/v1/metrics
```

**Response:**

```json
{
  "ingestion": {
    "packets_per_second": 5000,
    "messages_per_second": 3200,
    "parse_error_rate": 0.001
  },
  "inference": {
    "inferences_per_second": 3200,
    "latency_p50_ms": 12,
    "latency_p99_ms": 35
  },
  "alerting": {
    "alerts_per_hour": 5,
    "open_alerts": 12,
    "false_positive_rate": 0.15
  },
  "storage": {
    "timescaledb_size_gb": 45.2,
    "kafka_lag": 150
  }
}
```

### Health

#### Health Check

```http
GET /api/v1/health
```

**Response:**

```json
{
  "status": "healthy",
  "components": {
    "kafka": "healthy",
    "postgres": "healthy",
    "timescaledb": "healthy",
    "redis": "healthy",
    "inference": "healthy"
  },
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid severity value",
    "details": {
      "field": "severity",
      "allowed_values": ["critical", "high", "medium", "low"]
    }
  }
}
```

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | VALIDATION_ERROR | Invalid request parameters |
| 401 | UNAUTHORIZED | Missing or invalid auth |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |

## Rate Limiting

- **Default:** 100 requests/minute per API key
- **Burst:** Up to 20 requests/second
- Headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
