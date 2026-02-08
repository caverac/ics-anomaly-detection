# Redis

Redis is used by the **alerting service** for state management: storing incidents, tracking deduplication, and caching alert history.

## Why Redis?

### Speed

Redis is an in-memory data store with:

- Sub-millisecond latency
- 100,000+ operations/second
- No disk I/O for hot data

For real-time alerting, this speed is essential.

### Rich data structures

Redis provides more than key-value:

- **Hashes** for incident objects
- **Sorted sets** for time-ordered alert lists
- **Sets** for tracking unique IPs
- **Strings with TTL** for deduplication

### TTL support

Automatic expiration for:

- Deduplication windows (60 seconds)
- Alert history (7 days)
- Incident cache (24 hours)

No manual cleanup required.

### Pub/Sub

Redis pub/sub enables real-time updates:

- Dashboard notifications
- Alert broadcasting
- Service coordination

### Simplicity

Single Redis instance handles all alerting state. No complex distributed setup for development.

## Data structures used

### Incidents (Hashes)

```
incident:{id} → {
    correlation_key: "192.168.1.100:192.168.1.10:modbus"
    status: "active"
    priority: "P2"
    anomaly_count: 15
    ...
}
```

### Alert history (Sorted Sets)

```
alerts:by_time → [(timestamp1, alert_id1), (timestamp2, alert_id2), ...]
```

### Deduplication (Strings with TTL)

```
dedup:{key} → 1  (TTL: 60s)
```

### Incident lookups (Sets)

```
incidents:active → {incident_id1, incident_id2, ...}
incidents:by_correlation:{key} → incident_id
```

## Alternatives considered

| Alternative                 | Pros                          | Cons                                          |
| --------------------------- | ----------------------------- | --------------------------------------------- |
| **PostgreSQL**              | ACID, complex queries         | Slower for simple lookups, overkill           |
| **Memcached**               | Simple, fast                  | No persistence, limited data types            |
| **DynamoDB**                | Managed, scalable             | Cost, AWS lock-in, latency                    |
| **etcd**                    | Consistent, Kubernetes native | Not designed for high throughput              |
| **In-memory (Python dict)** | Simplest                      | Lost on restart, no sharing between instances |

## Limitations

### Memory-bound

All data must fit in RAM. For this use case:

- Incidents are small (~1KB each)
- 100K incidents ≈ 100MB
- Well within typical Redis capacity

### Single-threaded

Redis uses a single thread for commands. Mitigations:

- Commands are fast (microseconds)
- Use pipelining for batches
- Cluster mode for scaling

### No complex queries

Redis doesn't support SQL-like queries:

- Can't filter incidents by multiple fields efficiently
- Application-level filtering required
- For complex queries, need secondary index

### Persistence trade-offs

Redis persistence options:

- **RDB**: Point-in-time snapshots (may lose recent data)
- **AOF**: Append-only log (slower, larger files)
- **Neither**: Pure cache (data lost on restart)

We use AOF for durability:

```yaml
command: redis-server --appendonly yes
```

## Configuration

### docker-compose.yml

```yaml
redis:
  image: redis:7-alpine
  ports:
    - '6379:6379'
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
  healthcheck:
    test: redis-cli ping | grep PONG
```

### Python client

```python
import redis

client = redis.from_url("redis://localhost:6379")

# Store incident
client.hset(f"incident:{id}", mapping=incident.dict())

# Set TTL
client.expire(f"incident:{id}", 86400)  # 24 hours

# Deduplication check
if client.set(f"dedup:{key}", 1, nx=True, ex=60):
    # First occurrence
    process_alert(alert)
else:
    # Duplicate, suppress
    pass
```

## Monitoring

Key Redis metrics:

- `used_memory` - RAM usage
- `connected_clients` - Active connections
- `keyspace_hits/misses` - Cache efficiency
- `expired_keys` - TTL expirations

```bash
# Redis CLI
redis-cli INFO

# Monitor commands in real-time
redis-cli MONITOR
```
