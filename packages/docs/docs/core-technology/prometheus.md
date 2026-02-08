# Prometheus

Prometheus is used for **metrics collection and monitoring** across all services.

## Why Prometheus?

### Pull-based model

Prometheus scrapes metrics from services, which:

- Simplifies service code (just expose an endpoint)
- Works well with dynamic service discovery
- Allows independent scaling of monitoring

### Dimensional data model

Labels enable flexible querying:

```promql
# Total alerts by severity
sum(alerting_alerts_total) by (severity)

# 95th percentile latency
histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))
```

### PromQL

Prometheus Query Language is powerful for:

- Aggregations across services
- Rate calculations
- Alerting rules
- Dashboard queries

### Kubernetes-native

Prometheus is the standard for Kubernetes monitoring with:

- Service discovery
- Operator pattern
- Native integrations

### Grafana integration

Prometheus + Grafana is the de facto standard:

- Pre-built dashboards
- Rich visualization
- Alerting integration

## Metrics exposed

### Capture service (Go)

```
capture_packets_total
capture_packets_published_total
capture_packets_dropped_total
capture_bytes_total
capture_errors_total
```

### Parser service (Rust)

```
parser_messages_processed_total
parser_parse_errors_total
parser_processing_duration_seconds
```

### Feature Engine (Python)

```
feature_engine_windows_processed_total
feature_engine_messages_consumed_total
feature_engine_extraction_duration_seconds
```

### Anomaly Detection (Python)

```
anomaly_detection_predictions_total
anomaly_detection_anomalies_detected_total
anomaly_detection_inference_duration_seconds
```

### Alerting (Python)

```
alerting_alerts_processed_total
alerting_incidents_created_total
alerting_notifications_sent_total
alerting_dedup_suppressed_total
```

## Alternatives considered

| Alternative          | Pros                             | Cons                                     |
| -------------------- | -------------------------------- | ---------------------------------------- |
| **InfluxDB**         | Better for high-cardinality      | Different query language, less ecosystem |
| **Datadog**          | Managed, full-featured           | Cost, vendor lock-in                     |
| **CloudWatch**       | AWS native                       | AWS-only, limited PromQL                 |
| **Graphite**         | Mature                           | Older architecture, less flexible        |
| **Victoria Metrics** | Prometheus-compatible, efficient | Smaller community                        |

## Limitations

### Pull model challenges

Services must be reachable by Prometheus. In some network topologies, push-based might be easier.

### Local storage only

Prometheus stores data locally. For long-term storage, need:

- Remote write to Thanos/Cortex
- Or accept limited retention

### High cardinality

Too many unique label combinations cause memory issues:

```promql
# Bad: user_id as label with millions of users
http_requests_total{user_id="..."}

# Good: aggregate by endpoint
http_requests_total{endpoint="/api/alerts"}
```

### No distributed mode

Single Prometheus server. For HA, need:

- Multiple Prometheus instances
- Thanos or Cortex for federation

## Configuration

### prometheus.yml

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'capture'
    static_configs:
      - targets: ['capture:8081']

  - job_name: 'parser'
    static_configs:
      - targets: ['parser:8082']

  - job_name: 'alerting'
    static_configs:
      - targets: ['alerting:8084']
```

### Running

```bash
# Start with monitoring profile
make monitoring

# Access Prometheus
open http://localhost:9090

# Access Grafana
open http://localhost:3001  # admin/admin
```

## Client libraries

| Language | Library                    |
| -------- | -------------------------- |
| Go       | `prometheus/client_golang` |
| Rust     | `prometheus` crate         |
| Python   | `prometheus_client`        |

## Example: Python metrics

```python
from prometheus_client import Counter, Histogram

MESSAGES_PROCESSED = Counter(
    'messages_processed_total',
    'Total messages processed',
    ['protocol']
)

PROCESSING_TIME = Histogram(
    'processing_duration_seconds',
    'Time spent processing messages'
)

# Usage
MESSAGES_PROCESSED.labels(protocol='modbus').inc()
with PROCESSING_TIME.time():
    process_message(msg)
```
