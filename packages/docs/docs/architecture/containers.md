---
sidebar_position: 2
---

# Container Architecture

The Container diagram shows the high-level technical building blocks of the system.

## Container Overview

```mermaid
flowchart TB
    subgraph External["External"]
        ICS["🏭 ICS Network"]
        SIEM["📊 SIEM"]
        USER["👤 Users"]
    end

    subgraph System["ICS Anomaly Detection Engine"]
        subgraph Ingestion["Ingestion Layer"]
            CAP["📡 Packet Capture<br/><i>Go</i><br/>libpcap, gopacket"]
            PARSE["🔌 Protocol Parser<br/><i>Rust</i><br/>Modbus, DNP3, OPC-UA"]
        end

        subgraph Stream["Stream Processing"]
            KAFKA["📨 Event Bus<br/><i>Apache Kafka</i><br/>Message broker"]
            FEAT["⚙️ Feature Engine<br/><i>Python</i><br/>Time-series features"]
        end

        subgraph ML["ML Layer"]
            INF["🧠 Inference Service<br/><i>Python</i><br/>PyTorch, ONNX"]
            TRAIN["📚 Training Pipeline<br/><i>Python</i><br/>MLflow, Ray"]
            MODEL["📦 Model Registry<br/><i>MLflow</i><br/>Version control"]
        end

        subgraph API["API Layer"]
            REST["🌐 REST API<br/><i>TypeScript</i><br/>Fastify"]
            WS["🔄 WebSocket<br/><i>TypeScript</i><br/>Real-time updates"]
        end

        subgraph Storage["Storage Layer"]
            TSDB["📈 TimescaleDB<br/><i>PostgreSQL</i><br/>Time-series data"]
            PG["🗄️ PostgreSQL<br/><i>Metadata</i><br/>Alerts, configs"]
            REDIS["⚡ Redis<br/><i>Cache</i><br/>Hot data, sessions"]
        end

        subgraph UI["Presentation"]
            DASH["📊 Dashboard<br/><i>React</i><br/>Real-time monitoring"]
        end
    end

    ICS -->|"Packets"| CAP
    CAP -->|"Raw frames"| PARSE
    PARSE -->|"Parsed messages"| KAFKA
    KAFKA -->|"Events"| FEAT
    FEAT -->|"Feature vectors"| KAFKA
    KAFKA -->|"Features"| INF
    INF -->|"Anomaly scores"| KAFKA
    KAFKA -->|"Alerts"| REST
    KAFKA -->|"Alerts"| SIEM

    FEAT -->|"Training data"| TSDB
    TSDB -->|"Historical"| TRAIN
    TRAIN -->|"Models"| MODEL
    MODEL -->|"Load model"| INF

    REST -->|"Query"| PG
    REST -->|"Time-series"| TSDB
    REST -->|"Cache"| REDIS

    WS -->|"Subscribe"| KAFKA
    DASH -->|"HTTP"| REST
    DASH -->|"Stream"| WS
    USER --> DASH

    style CAP fill:#1d3557,color:#fff
    style PARSE fill:#1d3557,color:#fff
    style KAFKA fill:#457b9d,color:#fff
    style FEAT fill:#2a9d8f,color:#fff
    style INF fill:#e63946,color:#fff
    style TRAIN fill:#e63946,color:#fff
    style REST fill:#f4a261,color:#000
    style DASH fill:#e9c46a,color:#000
```

## Container Details

### Ingestion Layer

#### Packet Capture Service

| Attribute | Value |
|-----------|-------|
| Language | Go |
| Purpose | High-performance packet capture |
| Libraries | libpcap, gopacket |
| Input | Network TAP / SPAN port |
| Output | Raw Ethernet frames to Parser |

**Key Responsibilities:**
- Zero-copy packet capture from network interface
- BPF filtering for ICS protocol ports
- Buffering for burst traffic handling
- Health monitoring and stats export

**Resource Profile:**
- CPU: Low (kernel-offloaded capture)
- Memory: 512MB buffer pool
- Network: Line-rate capable

#### Protocol Parser

| Attribute | Value |
|-----------|-------|
| Language | Rust |
| Purpose | ICS protocol dissection |
| Libraries | nom (parser combinators) |
| Input | Raw frames from Capture |
| Output | Structured messages to Kafka |

**Supported Protocols:**

```mermaid
flowchart LR
    subgraph Protocols
        MOD["Modbus TCP<br/>Read/Write Coils<br/>Read/Write Registers"]
        DNP["DNP3<br/>Data Link Layer<br/>Application Layer"]
        OPC["OPC-UA<br/>Binary protocol<br/>Service requests"]
        EIP["Ethernet/IP<br/>CIP messages<br/>I/O data"]
    end
```

**Output Schema (Kafka message):**

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "protocol": "modbus",
  "src_ip": "192.168.1.10",
  "dst_ip": "192.168.1.100",
  "src_port": 49152,
  "dst_port": 502,
  "function_code": 3,
  "unit_id": 1,
  "register_address": 100,
  "register_count": 10,
  "response_time_ms": 12.5,
  "payload_size": 48,
  "raw_hex": "000100000006010300640010"
}
```

### Stream Processing Layer

#### Event Bus (Kafka)

| Attribute | Value |
|-----------|-------|
| Technology | Apache Kafka |
| Purpose | Event streaming backbone |
| Topics | See topic list below |

**Topic Architecture:**

```mermaid
flowchart LR
    subgraph Topics["Kafka Topics"]
        T1["ics.raw.modbus<br/><i>Parsed Modbus messages</i>"]
        T2["ics.raw.dnp3<br/><i>Parsed DNP3 messages</i>"]
        T3["ics.features<br/><i>Feature vectors</i>"]
        T4["ics.anomalies<br/><i>Detection results</i>"]
        T5["ics.alerts<br/><i>Deduplicated alerts</i>"]
    end

    PARSE[Parser] --> T1
    PARSE --> T2
    T1 --> FEAT[Feature Engine]
    T2 --> FEAT
    FEAT --> T3
    T3 --> INF[Inference]
    INF --> T4
    T4 --> ALERT[Alert Manager]
    ALERT --> T5
```

**Retention Policy:**
- Raw messages: 7 days
- Features: 30 days
- Alerts: 1 year

#### Feature Engine

| Attribute | Value |
|-----------|-------|
| Language | Python |
| Purpose | Time-series feature extraction |
| Libraries | NumPy, Pandas, tsfresh |
| Input | Parsed protocol messages |
| Output | Feature vectors |

**Feature Categories:**

| Category | Features | Window |
|----------|----------|--------|
| Volume | msg_count, bytes_total, unique_sources | 1m, 5m, 15m |
| Timing | inter_arrival_mean, inter_arrival_std, burst_score | 1m, 5m |
| Protocol | function_code_dist, error_rate, new_unit_ids | 5m, 15m |
| Network | unique_pairs, fan_out_ratio, scan_score | 5m, 15m |
| Payload | register_entropy, value_change_rate, outlier_values | 1m, 5m |

### ML Layer

#### Inference Service

| Attribute | Value |
|-----------|-------|
| Language | Python |
| Framework | PyTorch (ONNX runtime) |
| Purpose | Real-time anomaly scoring |
| SLA | < 50ms p99 latency |

**Model Ensemble:**

```mermaid
flowchart TB
    INPUT["Feature Vector<br/>(150 dimensions)"]

    subgraph Ensemble["Model Ensemble"]
        M1["Isolation Forest<br/><i>Point anomalies</i>"]
        M2["LSTM Autoencoder<br/><i>Sequence anomalies</i>"]
        M3["One-Class SVM<br/><i>Boundary detection</i>"]
    end

    AGG["Score Aggregator<br/><i>Weighted ensemble</i>"]

    OUTPUT["Anomaly Score<br/>(0.0 - 1.0)"]

    INPUT --> M1
    INPUT --> M2
    INPUT --> M3
    M1 --> AGG
    M2 --> AGG
    M3 --> AGG
    AGG --> OUTPUT

    style M1 fill:#e63946,color:#fff
    style M2 fill:#e63946,color:#fff
    style M3 fill:#e63946,color:#fff
```

#### Training Pipeline

| Attribute | Value |
|-----------|-------|
| Orchestration | Ray |
| Tracking | MLflow |
| Schedule | Daily retrain (configurable) |
| Data Source | TimescaleDB (labeled + unlabeled) |

**Training Workflow:**

```mermaid
stateDiagram-v2
    [*] --> FetchData
    FetchData --> ValidateData
    ValidateData --> FeatureSelection
    FeatureSelection --> TrainModels
    TrainModels --> Evaluate
    Evaluate --> Compare
    Compare --> Deploy: Better than baseline
    Compare --> Reject: Worse than baseline
    Deploy --> [*]
    Reject --> [*]
```

### Storage Layer

#### TimescaleDB (Time-Series)

| Attribute | Value |
|-----------|-------|
| Base | PostgreSQL 15 |
| Extension | TimescaleDB 2.x |
| Purpose | Feature storage, historical analysis |

**Schema:**

```sql
-- Hypertable for features
CREATE TABLE features (
    time        TIMESTAMPTZ NOT NULL,
    source_ip   INET,
    dest_ip     INET,
    protocol    TEXT,
    features    JSONB,
    PRIMARY KEY (time, source_ip, dest_ip)
);

SELECT create_hypertable('features', 'time');

-- Continuous aggregates for dashboards
CREATE MATERIALIZED VIEW features_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    source_ip,
    AVG((features->>'msg_count')::float) AS avg_msg_count,
    MAX((features->>'anomaly_score')::float) AS max_anomaly
FROM features
GROUP BY bucket, source_ip;
```

### API Layer

#### REST API

| Attribute | Value |
|-----------|-------|
| Language | TypeScript |
| Framework | Fastify |
| Auth | JWT + API Keys |
| Docs | OpenAPI 3.0 |

**Key Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/alerts` | List alerts (paginated) |
| GET | `/api/v1/alerts/:id` | Alert details |
| PATCH | `/api/v1/alerts/:id` | Update alert status |
| GET | `/api/v1/devices` | Discovered devices |
| GET | `/api/v1/metrics` | System health metrics |
| POST | `/api/v1/models/reload` | Hot-reload models |

### Presentation Layer

#### Dashboard

| Attribute | Value |
|-----------|-------|
| Framework | React 18 |
| State | Zustand |
| Charts | Apache ECharts |
| Real-time | WebSocket |

**Key Views:**
- **Overview**: System health, alert summary, top anomalies
- **Alerts**: Filterable alert list with severity/status
- **Investigation**: Alert drill-down with context
- **Devices**: Asset inventory with baseline status
- **Models**: ML model performance metrics
