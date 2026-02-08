# Apache Kafka

Kafka is the **backbone** of the data pipeline, connecting all services through message streams.

## Why Kafka?

### Designed for streaming

Kafka is purpose-built for high-throughput, low-latency streaming:

- Millions of messages per second
- Sub-millisecond latency
- Durable message storage

### Decoupling services

Kafka enables loose coupling:

- Producers don't know about consumers
- Services can be restarted independently
- New consumers can replay historical data

### Exactly-once semantics

Kafka provides strong delivery guarantees:

- At-least-once by default
- Exactly-once with transactions
- Ordered delivery within partitions

### Replay capability

Messages are persisted (default: 7 days), enabling:

- Reprocessing after bug fixes
- Training ML models on historical data
- Debugging production issues

### Ecosystem

Kafka has a rich ecosystem:

- Kafka Connect for integrations
- Kafka Streams for stream processing
- Schema Registry for data governance

## KRaft mode

We use **KRaft mode** (Kafka Raft) instead of ZooKeeper:

- Simpler deployment (no ZooKeeper cluster)
- Faster controller failover
- Reduced operational complexity
- Native to Kafka 3.x+

```yaml
# docker-compose.yml
KAFKA_PROCESS_ROLES: broker,controller
KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
```

## Topics

| Topic               | Purpose                   | Partitions |
| ------------------- | ------------------------- | ---------- |
| `ics.raw.packets`   | Raw captured packets      | 6          |
| `ics.parsed.modbus` | Parsed Modbus messages    | 6          |
| `ics.parsed.dnp3`   | Parsed DNP3 messages      | 6          |
| `ics.parsed.opcua`  | Parsed OPC-UA messages    | 6          |
| `ics.features`      | Extracted feature vectors | 6          |
| `ics.anomalies`     | Detected anomalies        | 6          |
| `ics.alerts`        | Generated alerts          | 3          |

## Alternatives considered

| Alternative        | Pros                          | Cons                                  |
| ------------------ | ----------------------------- | ------------------------------------- |
| **RabbitMQ**       | Simpler, good for task queues | Not designed for streaming, no replay |
| **Redis Streams**  | Simple, low latency           | Less mature, limited partitioning     |
| **Apache Pulsar**  | Multi-tenancy, tiered storage | More complex, smaller community       |
| **AWS Kinesis**    | Managed service               | Vendor lock-in, cost                  |
| **NATS JetStream** | Lightweight, simple           | Smaller ecosystem                     |

## Limitations

### Operational complexity

Kafka clusters require:

- Monitoring (lag, throughput, disk usage)
- Capacity planning
- Rebalancing during scaling

For development, single-node KRaft simplifies this significantly.

### Message size limits

Default max message size is 1MB. For ICS traffic this is rarely an issue (packets are small).

### No built-in message filtering

Consumers receive all messages in subscribed partitions. Filtering happens in application code.

### Java dependency

Kafka is written in Java. While we use librdkafka (C) clients, the broker requires JVM.

### Learning curve

Understanding partitions, consumer groups, offsets, and rebalancing takes time.

## Configuration

### Single-node development settings

```yaml
# Required for single-node KRaft
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
```

### Client configuration

```python
# Python (confluent-kafka)
Producer({
    "bootstrap.servers": "kafka:9092",
    "compression.type": "gzip",
    "batch.size": 16384,
    "linger.ms": 5,
})

Consumer({
    "bootstrap.servers": "kafka:9092",
    "group.id": "my-consumer-group",
    "auto.offset.reset": "earliest",
})
```

## Monitoring

Use Kafka UI for development:

```bash
make debug  # Starts Kafka UI at localhost:8080
```

Key metrics to monitor:

- Consumer lag
- Throughput (messages/sec)
- Partition distribution
- Broker disk usage
