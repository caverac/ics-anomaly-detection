---
sidebar_position: 3
---

# Troubleshooting

Common issues and solutions.

## No Alerts Generated

**Symptoms:** System running but no alerts appearing.

**Checklist:**

1. **Check simulator is running:**

   ```bash
   curl http://localhost:8083/status
   # Should show {"running": true, ...}
   ```

2. **Verify Kafka topics have data:**

   ```bash
   # Check raw packets
   docker compose exec kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic ics.raw.packets --max-messages 3

   # Check features
   docker compose exec kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic ics.features --max-messages 3

   # Check anomalies
   docker compose exec kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic ics.anomalies --max-messages 3
   ```

3. **Check service health:**

   ```bash
   curl http://localhost:8082/health  # Feature engine
   curl http://localhost:8085/health  # Anomaly detection
   curl http://localhost:8084/health  # Alerting
   ```

4. **Check for errors in logs:**

   ```bash
   docker compose logs --tail 50 anomaly-detection
   docker compose logs --tail 50 alerting
   ```

5. **Verify alert thresholds:**
   - Anomaly scores may be below threshold
   - Try triggering an attack to generate higher scores:
     ```bash
     curl -X POST http://localhost:8083/attack/start \
       -H "Content-Type: application/json" \
       -d '{"mode": "reconnaissance"}'
     ```

## Services Not Starting

**Symptoms:** Containers exit or restart repeatedly.

### Kafka Not Ready

```bash
# Check Kafka logs
docker compose logs kafka

# Common issues:
# - "Cluster ID doesn't match" → delete volumes: docker compose down -v
# - Port conflicts → check nothing else on 9092
```

**Solution:** Ensure Kafka is healthy before starting dependent services:

```bash
# Wait for Kafka
docker compose up -d kafka
sleep 10
docker compose up -d
```

### Redis Connection Failed

```bash
# Check Redis
docker compose logs redis
docker compose exec redis redis-cli ping
# Should return: PONG
```

### Port Conflicts

```bash
# Check if ports are in use
lsof -i :8083  # Simulator
lsof -i :8084  # Alerting
lsof -i :9092  # Kafka
```

## High False Positive Rate

**Solutions:**

1. **Check anomaly distribution:**

   ```bash
   curl http://localhost:8084/stats
   # High dedup_suppressed indicates repeated alerts
   ```

2. **Adjust traffic patterns:**

   ```bash
   # Reduce simulator rate
   curl -X POST http://localhost:8083/config \
     -H "Content-Type: application/json" \
     -d '{"rate": 50}'
   ```

3. **Review feature values:**
   ```bash
   # Sample features
   docker compose exec kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic ics.features --max-messages 5 | jq
   ```

## High Latency

**Check bottlenecks:**

```bash
# Check Kafka consumer lag
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group anomaly-detection

# Check service latency metrics
curl -s http://localhost:8085/metrics | grep latency
```

**Solutions:**

- Scale feature engine workers (increase `WORKER_COUNT`)
- Reduce simulator message rate
- Check container resource limits

## Kafka Issues

### Consumer Not Receiving Messages

```bash
# Check consumer groups
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --list

# Check specific group
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group anomaly-detection
```

### Topics Not Created

```bash
# List topics
docker compose exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list

# Manually create if needed
docker compose exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic ics.features \
  --partitions 6 --replication-factor 1
```

### Consumer Lag High

```bash
# Check lag
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group feature-engine

# Reset offsets (CAUTION: skips messages)
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --reset-offsets --to-latest \
  --topic ics.raw.packets \
  --group feature-engine --execute
```

### Disk Space Issues

```bash
# Check Kafka data size
docker compose exec kafka du -sh /var/lib/kafka/data

# Reduce retention (temporary)
docker compose exec kafka kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --alter --topic ics.raw.packets \
  --add-config retention.ms=86400000  # 1 day
```

## Redis Issues

### Connection Refused

```bash
# Check Redis is running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping

# Check Redis logs
docker compose logs redis
```

### Memory Issues

```bash
# Check Redis memory
docker compose exec redis redis-cli info memory

# Clear data if needed (loses state)
docker compose exec redis redis-cli FLUSHALL
```

## Model Issues

### Low Detection Rate

1. **Check feature values are reasonable:**

   ```bash
   docker compose exec kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic ics.features --max-messages 1 | jq
   ```

2. **Verify models are loaded:**

   ```bash
   docker compose logs anomaly-detection | grep -i model
   ```

3. **Check inference is running:**
   ```bash
   curl http://localhost:8085/health
   ```

### Model Not Loading

```bash
# Check model files exist
docker compose exec anomaly-detection ls -la /app/models/

# Check for import errors
docker compose logs anomaly-detection | grep -i error
```

## Complete Reset

If all else fails, reset everything:

```bash
# Stop and remove everything
docker compose down -v

# Remove any cached images (optional)
docker compose build --no-cache

# Start fresh
docker compose up -d
```

## Collecting Debug Information

When reporting issues:

```bash
# System info
echo "=== Docker Version ===" && docker version
echo "=== Docker Compose Version ===" && docker compose version
echo "=== Container Status ===" && docker compose ps
echo "=== Resource Usage ===" && docker stats --no-stream
echo "=== Recent Logs ===" && docker compose logs --tail 50
```
