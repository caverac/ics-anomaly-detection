---
sidebar_position: 1
---

# REST API

API reference for the Alerting Service.

## Overview

The alerting service exposes a REST API for querying and managing alerts and incidents. Built with FastAPI, it provides endpoints for alert management, incident tracking, and service health monitoring.

## Base URL

```
http://localhost:8084
```

## Authentication

:::note Current Implementation
Authentication is not currently implemented. The API is intended for internal use within the Docker network.
:::

## Service Endpoints

### Health Check

Check service health status.

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "kafka_connected": true,
  "redis_connected": true
}
```

| Status     | Description                 |
| ---------- | --------------------------- |
| `healthy`  | All connections operational |
| `degraded` | Some connections failing    |

### Metrics

Get Prometheus-compatible metrics.

```http
GET /metrics
```

**Response:**

```json
{
  "alerting_alerts_processed_total": 1250,
  "alerting_incidents_created_total": 45,
  "alerting_incidents_updated_total": 120,
  "alerting_notifications_sent_total": 89,
  "alerting_alerts_suppressed_total": 340,
  "alerting_escalations_total": 12
}
```

### Statistics

Get service statistics summary.

```http
GET /stats
```

**Response:**

```json
{
  "alerts_processed": 1250,
  "incidents_created": 45,
  "incidents_updated": 120,
  "notifications_sent": 89,
  "dedup_suppressed": 340,
  "escalations": 12
}
```

## Alert Endpoints

### List Alerts

Retrieve recent alerts with optional filtering.

```http
GET /alerts
```

**Query Parameters:**

| Parameter  | Type   | Default | Description                                 |
| ---------- | ------ | ------- | ------------------------------------------- |
| `limit`    | int    | 50      | Maximum alerts to return                    |
| `status`   | string | -       | Filter: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`  |
| `severity` | string | -       | Filter: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |

**Response:**

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "incident_id": "i9j8k7l6-m5n4-3210-wxyz-ab9876543210",
    "created_at": "2024-01-15T10:30:00.123456Z",
    "severity": "HIGH",
    "status": "OPEN",
    "title": "RECONNAISSANCE detected from 192.168.1.50",
    "description": "Elevated fc_unique_count (8) indicates device scanning",
    "source": {
      "src_ip": "192.168.1.50",
      "dst_ip": "192.168.1.10",
      "protocol": "modbus"
    },
    "anomaly_type": "RECONNAISSANCE",
    "ensemble_score": 0.89,
    "confidence": 0.85,
    "related_anomaly_count": 1,
    "feature_contributions": {
      "fc_unique_count": 0.45,
      "fc_entropy": 0.32,
      "fc_diagnostic_ratio": 0.23
    }
  }
]
```

### Get Alert Details

Get a specific alert by ID.

```http
GET /alerts/{alert_id}
```

**Response:** Same schema as list item.

**Errors:**

- `404` - Alert not found

### Acknowledge Alert

Mark an alert as acknowledged.

```http
POST /alerts/{alert_id}/acknowledge
```

**Response:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "ACKNOWLEDGED",
  "acknowledged": true
}
```

### Resolve Alert

Mark an alert as resolved.

```http
POST /alerts/{alert_id}/resolve
```

**Response:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "RESOLVED",
  "acknowledged": true
}
```

## Incident Endpoints

Incidents group related anomalies by correlation key (`{src_ip}:{dst_ip}:{protocol}`).

### List Incidents

```http
GET /incidents
```

**Query Parameters:**

| Parameter | Type   | Default | Description                                  |
| --------- | ------ | ------- | -------------------------------------------- |
| `limit`   | int    | 50      | Maximum incidents to return                  |
| `status`  | string | -       | Filter: `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED` |

**Response:**

```json
[
  {
    "id": "i9j8k7l6-m5n4-3210-wxyz-ab9876543210",
    "correlation_key": "192.168.1.50:192.168.1.10:modbus",
    "status": "ACTIVE",
    "priority": "P2",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "anomaly_count": 5,
    "alert_ids": ["a1b2c3d4..."],
    "max_ensemble_score": 0.92,
    "src_ips": ["192.168.1.50"],
    "dst_ips": ["192.168.1.10", "192.168.1.11"],
    "anomaly_types": ["RECONNAISSANCE"]
  }
]
```

### Get Incident Details

```http
GET /incidents/{incident_id}
```

**Response:** Same schema as list item.

### Acknowledge Incident

```http
POST /incidents/{incident_id}/acknowledge
```

### Resolve Incident

```http
POST /incidents/{incident_id}/resolve
```

## Alert Schema

### AlertSeverity

| Value      | Description                    |
| ---------- | ------------------------------ |
| `LOW`      | Minor deviation, informational |
| `MEDIUM`   | Moderate anomaly, investigate  |
| `HIGH`     | Significant threat indicator   |
| `CRITICAL` | Immediate action required      |

### AlertStatus

| Value          | Description                    |
| -------------- | ------------------------------ |
| `OPEN`         | New, unacknowledged alert      |
| `ACKNOWLEDGED` | Analyst is aware/investigating |
| `RESOLVED`     | Alert has been addressed       |

### AnomalyType

| Value                 | MITRE Mapping |
| --------------------- | ------------- |
| `RECONNAISSANCE`      | T0846         |
| `TIMING_ANOMALY`      | T0882         |
| `VOLUME_ANOMALY`      | -             |
| `PROTOCOL_VIOLATION`  | T0855         |
| `UNAUTHORIZED_ACCESS` | T0821         |
| `DATA_EXFILTRATION`   | T0882         |
| `COMMAND_INJECTION`   | T0831         |
| `UNKNOWN`             | -             |

## Incident Schema

### IncidentStatus

| Value          | Description        |
| -------------- | ------------------ |
| `ACTIVE`       | Ongoing incident   |
| `ACKNOWLEDGED` | Being investigated |
| `RESOLVED`     | Incident closed    |

### IncidentPriority

| Priority | Criteria                                           |
| -------- | -------------------------------------------------- |
| `P4`     | Initial incident (< 5 anomalies)                   |
| `P3`     | 5+ anomalies in window                             |
| `P2`     | 10+ anomalies or HIGH severity                     |
| `P1`     | 20+ anomalies or CRITICAL severity or multi-target |

## Error Responses

Errors follow FastAPI conventions:

```json
{
  "detail": "Alert not found"
}
```

| Status | Description           |
| ------ | --------------------- |
| `404`  | Resource not found    |
| `422`  | Validation error      |
| `500`  | Internal server error |

## Example Usage

### List Critical Alerts

```bash
curl "http://localhost:8084/alerts?severity=CRITICAL&status=OPEN"
```

### Acknowledge an Alert

```bash
curl -X POST http://localhost:8084/alerts/a1b2c3d4-e5f6-7890-abcd-ef1234567890/acknowledge
```

### Get Active Incidents

```bash
curl "http://localhost:8084/incidents?status=ACTIVE"
```

### Check Service Health

```bash
curl http://localhost:8084/health
```
