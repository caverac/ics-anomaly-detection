---
sidebar_position: 3
---

# Prometheus Metrics

All services expose metrics on `/metrics` endpoint in Prometheus format.

## Service Metric Endpoints

| Service | Port | Endpoint |
|---------|------|----------|
| Simulator | 8083 | `/metrics` |
| Feature Engine | 8082 | `/metrics` |
| Anomaly Detection | 8085 | `/metrics` |
| Alerting | 8084 | `/metrics` |

## Simulator Metrics

```promql
# Messages sent per second by protocol
rate(simulator_messages_sent_total{protocol="modbus"}[1m])

# Total errors
simulator_errors_total

# Message generation latency
histogram_quantile(0.99, simulator_message_latency_seconds_bucket)
```

## Feature Engine Metrics

```promql
# Messages processed
rate(feature_engine_messages_processed_total[1m])

# Feature extraction latency
histogram_quantile(0.95, feature_engine_extraction_latency_seconds_bucket)

# Windows emitted
rate(feature_engine_windows_emitted_total[1m])
```

## Anomaly Detection Metrics

```promql
# Inference throughput
rate(anomaly_detection_inferences_total[1m])

# Inference latency by model
histogram_quantile(0.99, anomaly_detection_inference_latency_seconds_bucket{model="isolation_forest"})

# Anomaly score distribution
anomaly_detection_score_bucket

# Anomalies detected by type
rate(anomaly_detection_anomalies_total{type="RECONNAISSANCE"}[5m])
```

## Alerting Metrics

```promql
# Alerts generated
rate(alerting_alerts_processed_total[1h])

# Alerts suppressed (deduplicated)
alerting_alerts_suppressed_total

# Incidents created
alerting_incidents_created_total

# Notifications sent
alerting_notifications_sent_total

# Escalations triggered
alerting_escalations_total
```

## Kafka Metrics

If using Kafka with JMX exporter:

```promql
# Consumer lag
kafka_consumer_fetch_manager_records_lag

# Messages per second
rate(kafka_server_brokertopicmetrics_messagesin_total[1m])

# Topic size
kafka_log_log_size
```

## Common Queries

### System Health

```promql
# Overall ingestion rate
sum(rate(simulator_messages_sent_total[1m]))

# End-to-end pipeline throughput
sum(rate(alerting_alerts_processed_total[1m]))

# Error rate across services
sum(rate({__name__=~".*_errors_total"}[5m]))
```

### Performance

```promql
# p99 latency for anomaly detection
histogram_quantile(0.99,
  sum(rate(anomaly_detection_inference_latency_seconds_bucket[5m])) by (le)
)

# Feature extraction rate
sum(rate(feature_engine_windows_emitted_total[1m]))
```

### Detection Quality

```promql
# Anomaly detection rate by type
sum by (type) (rate(anomaly_detection_anomalies_total[1h]))

# Alert to anomaly ratio (indicates threshold effectiveness)
sum(rate(alerting_alerts_processed_total[1h])) /
sum(rate(anomaly_detection_anomalies_total[1h]))
```

## Grafana Integration

Pre-built dashboards are available in `/config/grafana/provisioning/dashboards/`:

### Overview Dashboard

Displays:
- Message throughput (simulator → features → anomalies)
- Alert generation rate
- Service health status
- Resource utilization

### Detection Dashboard

Displays:
- Anomaly score distribution over time
- Alerts by type and severity
- Top source/destination pairs
- Feature value trends

## Scrape Configuration

Example Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'ics-anomaly-detection'
    static_configs:
      - targets:
          - 'simulator:8083'
          - 'feature-engine:8082'
          - 'anomaly-detection:8085'
          - 'alerting:8084'
    scrape_interval: 15s
```

## Adding Custom Metrics

Services use `prometheus_client` for Python:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
MY_COUNTER = Counter('my_service_operations_total', 'Total operations', ['type'])
MY_HISTOGRAM = Histogram('my_service_latency_seconds', 'Operation latency')

# Use in code
MY_COUNTER.labels(type='read').inc()
with MY_HISTOGRAM.time():
    do_operation()

# Expose endpoint (FastAPI)
@app.get('/metrics')
async def metrics():
    return Response(content=generate_latest(), media_type='text/plain')
```
