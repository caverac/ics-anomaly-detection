---
sidebar_position: 3
---

# Prometheus Metrics

All services expose metrics on `/metrics` endpoint in Prometheus format.

## Key Metrics

### Ingestion

```promql
# Packets captured per second
rate(packets_captured_total[1m])

# Parse errors
rate(parse_errors_total[5m])

# Capture buffer utilization
capture_buffer_utilization_percent
```

### Inference

```promql
# Inference throughput
rate(inference_total[1m])

# Inference latency
histogram_quantile(0.99, inference_latency_seconds_bucket)

# Model-specific scores
anomaly_score_bucket{model="isolation_forest"}
```

### Alerting

```promql
# Alerts generated
rate(alerts_generated_total[1h])

# Alerts by severity
alerts_generated_total{severity="critical"}

# Alert processing latency
histogram_quantile(0.95, alert_processing_latency_seconds_bucket)
```

## Grafana Dashboards

Pre-built dashboards are available in `/dashboards/`:

- **Overview** - System health and throughput
- **Inference** - ML model performance
- **Alerts** - Alert trends and breakdown
- **Devices** - Per-device statistics
