---
sidebar_position: 4
---

# Data Flow Architecture

This page describes how data flows through the system from capture to alert.

## End-to-End Data Flow

```mermaid
flowchart TB
    subgraph Source["1. Data Source"]
        ICS["ICS Network<br/>Modbus/DNP3/OPC-UA"]
        TAP["Network TAP"]
    end

    subgraph Capture["2. Capture & Parse"]
        CAP["Packet Capture<br/><i>~100K pps</i>"]
        PARSE["Protocol Parser<br/><i>~50K msgs/s</i>"]
    end

    subgraph Stream["3. Stream Processing"]
        K1["Kafka: ics.raw.*<br/><i>Parsed messages</i>"]
        FEAT["Feature Engine<br/><i>~10K vectors/s</i>"]
        K2["Kafka: ics.features<br/><i>Feature vectors</i>"]
    end

    subgraph ML["4. ML Inference"]
        INF["Inference Service<br/><i>~10K inferences/s</i>"]
        K3["Kafka: ics.anomalies<br/><i>Scored events</i>"]
    end

    subgraph Alert["5. Alert Processing"]
        AM["Alert Manager"]
        K4["Kafka: ics.alerts<br/><i>Deduplicated alerts</i>"]
    end

    subgraph Output["6. Output"]
        REDIS["Redis<br/><i>Incident state</i>"]
        SIEM["SIEM<br/><i>External</i>"]
        DASH["Dashboard<br/><i>Real-time</i>"]
    end

    ICS --> TAP
    TAP --> CAP
    CAP --> PARSE
    PARSE --> K1
    K1 --> FEAT
    FEAT --> K2
    K2 --> INF
    INF --> K3
    K3 --> AM
    AM --> REDIS
    AM --> K4
    K4 --> SIEM
    K4 --> DASH

    style K1 fill:#457b9d,color:#fff
    style K2 fill:#457b9d,color:#fff
    style K3 fill:#457b9d,color:#fff
    style K4 fill:#457b9d,color:#fff
    style INF fill:#e63946,color:#fff
```

## Detailed Stage Flows

### Stage 1: Packet Capture Flow

```mermaid
sequenceDiagram
    participant NET as ICS Network
    participant TAP as Network TAP
    participant NIC as Capture NIC
    participant RING as Ring Buffer
    participant CAP as Capture Process
    participant PARSE as Parser

    NET->>TAP: Traffic (mirror)
    TAP->>NIC: Copied packets
    NIC->>RING: DMA to ring buffer
    Note over RING: Zero-copy capture

    loop Every 1ms
        CAP->>RING: Poll for packets
        RING->>CAP: Batch of packets
        CAP->>CAP: BPF filter (ports 502, 20000, 4840)
        CAP->>PARSE: Filtered packets via Unix socket
    end
```

**Performance Characteristics:**

| Metric | Value |
|--------|-------|
| Max throughput | 10 Gbps line rate |
| Latency (TAP to Parser) | < 1ms p99 |
| Packet loss at max load | < 0.01% |
| Buffer size | 512MB ring buffer |

### Stage 2: Protocol Parsing Flow

```mermaid
sequenceDiagram
    participant CAP as Capture
    participant DIS as Dispatcher
    participant MOD as Modbus Parser
    participant DNP as DNP3 Parser
    participant SER as Serializer
    participant KAFKA as Kafka

    CAP->>DIS: Raw packet
    DIS->>DIS: Identify protocol (port/magic)

    alt Modbus (port 502)
        DIS->>MOD: Parse Modbus
        MOD->>MOD: Extract MBAP header
        MOD->>MOD: Parse function code
        MOD->>MOD: Extract registers/coils
        MOD->>SER: Structured message
    else DNP3 (port 20000)
        DIS->>DNP: Parse DNP3
        DNP->>DNP: Data link layer
        DNP->>DNP: Transport layer
        DNP->>DNP: Application layer
        DNP->>SER: Structured message
    end

    SER->>SER: JSON serialize
    SER->>KAFKA: Produce to ics.raw.{protocol}
```

**Parser Output Schema:**

```mermaid
erDiagram
    ParsedMessage {
        string timestamp
        string protocol
        string src_ip
        string dst_ip
        int src_port
        int dst_port
        string session_id
        json protocol_data
        bytes raw_payload
    }

    ModbusData {
        int unit_id
        int function_code
        int start_address
        int quantity
        bytes values
        bool is_response
        int exception_code
    }

    DNP3Data {
        int source_address
        int destination_address
        int function_code
        json objects
        bool is_response
        int internal_indications
    }

    ParsedMessage ||--o| ModbusData : "contains"
    ParsedMessage ||--o| DNP3Data : "contains"
```

### Stage 3: Feature Extraction Flow

```mermaid
sequenceDiagram
    participant KAFKA as Kafka (ics.raw.*)
    participant WM as Window Manager
    participant BUF as Buffer
    participant EXT as Extractors
    participant AGG as Aggregators
    participant OUT as Output

    loop Continuous
        KAFKA->>WM: Batch of messages

        WM->>WM: Assign to windows (1m, 5m, 15m)
        WM->>BUF: Buffer by window

        Note over WM: On window close

        BUF->>EXT: Window messages
        EXT->>EXT: Extract protocol features
        EXT->>AGG: Raw features

        par Volume aggregation
            AGG->>AGG: Count, sum, unique
        and Timing aggregation
            AGG->>AGG: IAT stats, burst detection
        and Protocol aggregation
            AGG->>AGG: Function code dist, errors
        end

        AGG->>OUT: Feature vector
        OUT->>KAFKA: Produce to ics.features
    end
```

**Feature Window State Machine:**

```mermaid
stateDiagram-v2
    [*] --> Open: Window start
    Open --> Accumulating: Receive message
    Accumulating --> Accumulating: More messages
    Accumulating --> Closing: Window end time
    Closing --> Extracting: Flush buffer
    Extracting --> Publishing: Features computed
    Publishing --> [*]: Vector sent

    note right of Accumulating
        Messages buffered
        per (src_ip, dst_ip, protocol)
    end note
```

### Stage 4: ML Inference Flow

```mermaid
sequenceDiagram
    participant KAFKA as Kafka (ics.features)
    participant NORM as Normalizer
    participant CACHE as Model Cache
    participant IF as Isolation Forest
    participant LSTM as LSTM-AE
    participant SVM as One-Class SVM
    participant AGG as Aggregator
    participant OUT as Output

    KAFKA->>NORM: Feature vector

    NORM->>NORM: Z-score normalize
    Note over NORM: Using stored μ, σ

    par Model inference (parallel)
        NORM->>IF: Normalized vector
        IF->>IF: Compute anomaly score
        IF->>AGG: Score: 0.23
    and
        NORM->>LSTM: Normalized sequence
        LSTM->>LSTM: Encode → Decode
        LSTM->>LSTM: Reconstruction error
        LSTM->>AGG: Score: 0.67
    and
        NORM->>SVM: Normalized vector
        SVM->>SVM: Distance from boundary
        SVM->>AGG: Score: 0.12
    end

    AGG->>AGG: Weighted average
    Note over AGG: 0.4*IF + 0.4*LSTM + 0.2*SVM
    AGG->>OUT: Final score: 0.42
    OUT->>KAFKA: Produce to ics.anomalies
```

**Inference Latency Breakdown:**

```mermaid
gantt
    title Inference Latency (p99)
    dateFormat X
    axisFormat %L ms

    section Pipeline
    Kafka consume     :0, 5
    Normalization     :5, 7
    Isolation Forest  :7, 12
    LSTM-AE          :7, 25
    One-Class SVM    :7, 10
    Aggregation      :25, 27
    Kafka produce    :27, 32

    section SLA
    Target (50ms)    :crit, 0, 50
```

### Stage 5: Alert Processing Flow

```mermaid
sequenceDiagram
    participant KAFKA as Kafka (ics.anomalies)
    participant CORR as Correlator
    participant DEDUP as Deduplicator
    participant ESCAL as Escalation Manager
    participant REDIS as Redis
    participant NOTIFY as Notifier

    KAFKA->>CORR: Anomaly result
    CORR->>CORR: Find/create incident (5min window)
    CORR->>REDIS: Update incident

    CORR->>DEDUP: Check for duplicates
    DEDUP->>REDIS: Check dedup key

    alt New alert
        DEDUP->>ESCAL: Process alert
        ESCAL->>ESCAL: Calculate priority (P4-P1)
        ESCAL->>REDIS: Store alert

        par Parallel dispatch
            ESCAL->>KAFKA: Publish to ics.alerts
            ESCAL->>NOTIFY: Send notifications
        end
    else Duplicate
        DEDUP->>DEDUP: Suppress
        Note over DEDUP: Within 60s window
    end
```

## Data Retention Policy

```mermaid
flowchart LR
    subgraph Hot["Hot Storage"]
        R1["Raw messages<br/><i>Kafka (7 days)</i>"]
        F1["Feature vectors<br/><i>Kafka (7 days)</i>"]
        A1["Anomalies<br/><i>Kafka (7 days)</i>"]
    end

    subgraph State["State Storage"]
        I1["Incidents<br/><i>Redis (24 hours)</i>"]
        AL1["Alerts<br/><i>Redis (7 days)</i>"]
        D1["Dedup keys<br/><i>Redis (60 seconds)</i>"]
    end

    R1 --> F1
    F1 --> A1
    A1 --> AL1
    AL1 --> I1
```

**Retention Settings:**

| Data | Storage | TTL |
|------|---------|-----|
| Raw packets | Kafka | 7 days |
| Parsed messages | Kafka | 7 days |
| Feature vectors | Kafka | 7 days |
| Anomaly results | Kafka | 7 days |
| Alerts | Redis | 7 days |
| Incidents | Redis | 24 hours |
| Deduplication keys | Redis | 60 seconds |

## Throughput & Scaling

| Stage | Single Instance | Horizontal Scaling |
|-------|-----------------|-------------------|
| Packet Capture | 100K pps | Multiple interfaces |
| Protocol Parser | 50K msgs/s | Partition by source IP |
| Feature Engine | 10K vectors/s | Partition by Kafka partition |
| Inference Service | 10K inferences/s | Replicas + GPU optional |
| Alert Manager | 1K alerts/s | Single instance sufficient |

**Kafka Partition Strategy:**

```mermaid
flowchart TB
    subgraph Partitioning
        MSG["Incoming Message"]
        HASH["Hash: src_ip + dst_ip"]
        P0["Partition 0"]
        P1["Partition 1"]
        P2["Partition 2"]
        P3["Partition 3"]
    end

    MSG --> HASH
    HASH --> P0
    HASH --> P1
    HASH --> P2
    HASH --> P3

    Note["Same device pair always\ngoes to same partition\n→ Enables stateful processing"]
```
