---
sidebar_position: 3
---

# Troubleshooting

Common issues and solutions.

## No Alerts Generated

**Symptoms:** System running but no alerts appearing.

**Checklist:**

1. **Check traffic is being captured:**
   ```bash
   docker compose logs capture | tail -20
   # Should show packet counts
   ```

2. **Verify Kafka topics have data:**
   ```bash
   docker compose exec kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic ics.features --max-messages 5
   ```

3. **Check inference service:**
   ```bash
   curl http://localhost:8082/health
   ```

4. **Verify threshold configuration:**
   - Is `anomaly_score` threshold too high?
   - Are suppression rules blocking alerts?

## High False Positive Rate

**Solutions:**

1. **Increase threshold:**
   ```yaml
   thresholds:
     global:
       anomaly_score: 0.8  # Increase from 0.7
   ```

2. **Retrain models with more data:**
   ```bash
   ./scripts/retrain.sh --days 30
   ```

3. **Add suppression rules for known patterns:**
   ```yaml
   suppression:
     rules:
       - match:
           source_ip: "192.168.1.100"  # HMI
           type: "TIMING_ANOMALY"
         action: "suppress"
   ```

## High Latency

**Check bottlenecks:**

```bash
# Kafka lag
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group inference-service

# Inference latency
curl -s http://localhost:8082/metrics | grep inference_latency
```

**Solutions:**

- Scale inference service replicas
- Enable GPU acceleration
- Increase batch size

## Kafka Issues

### Consumer Lag

```bash
# Check lag
kafka-consumer-groups.sh --describe --group inference-service

# Reset offsets (CAUTION: loses messages)
kafka-consumer-groups.sh --reset-offsets --to-latest \
  --topic ics.features --group inference-service --execute
```

### Out of Disk

```bash
# Check disk usage
df -h /var/lib/kafka

# Reduce retention
kafka-configs.sh --alter --topic ics.raw.modbus \
  --add-config retention.ms=86400000  # 1 day
```

## Database Issues

### TimescaleDB Slow Queries

```sql
-- Check chunk sizes
SELECT * FROM timescaledb_information.chunks
WHERE hypertable_name = 'features'
ORDER BY range_start DESC LIMIT 10;

-- Compress old chunks
SELECT compress_chunk(c) FROM show_chunks('features', older_than => interval '7 days') c;
```

### Connection Pool Exhausted

Increase pool size in config:

```yaml
database:
  pool_size: 20  # Increase from default 10
```

## Model Issues

### Model Not Loading

```bash
# Check MLflow
curl http://localhost:5000/api/2.0/mlflow/registered-models/list

# Verify model stage
curl http://localhost:5000/api/2.0/mlflow/registered-models/get-latest-versions \
  -d '{"name": "isolation_forest", "stages": ["Production"]}'
```

### Poor Detection

1. Check for data drift:
   ```bash
   ./scripts/check-drift.sh
   ```

2. Review feature distributions:
   ```sql
   SELECT
     percentile_cont(0.5) WITHIN GROUP (ORDER BY (features->>'msg_count_5m')::float) as median
   FROM features
   WHERE time > now() - interval '1 day';
   ```

3. Trigger retraining:
   ```bash
   curl -X POST http://localhost:8082/models/retrain
   ```
