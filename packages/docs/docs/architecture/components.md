---
sidebar_position: 3
---

# Component Architecture

This page details the internal components of key containers.

## Inference Service Components

The Inference Service is the core ML engine responsible for real-time anomaly detection.

```mermaid
flowchart TB
    subgraph InferenceService["Inference Service"]
        subgraph Input["Input Layer"]
            KC["Kafka Consumer<br/><i>Batch consumer</i>"]
            VAL["Input Validator<br/><i>Schema validation</i>"]
            NORM["Normalizer<br/><i>Feature scaling</i>"]
        end

        subgraph Models["Model Layer"]
            ML["Model Loader<br/><i>ONNX runtime</i>"]
            CACHE["Model Cache<br/><i>Hot models in memory</i>"]

            subgraph Ensemble["Detection Models"]
                IF["Isolation Forest"]
                LSTM["LSTM-AE"]
                OCSVM["One-Class SVM"]
            end
        end

        subgraph Scoring["Scoring Layer"]
            AGG["Score Aggregator<br/><i>Weighted ensemble</i>"]
            THRESH["Threshold Engine<br/><i>Adaptive thresholds</i>"]
            CLASS["Classifier<br/><i>Anomaly type labeling</i>"]
        end

        subgraph Output["Output Layer"]
            DEDUP["Deduplicator<br/><i>Suppress duplicates</i>"]
            ENRICH["Enricher<br/><i>Add context</i>"]
            KP["Kafka Producer<br/><i>Publish alerts</i>"]
        end
    end

    KAFKA_IN["Kafka<br/>ics.features"] --> KC
    KC --> VAL
    VAL --> NORM
    NORM --> Ensemble
    ML --> CACHE
    CACHE --> Ensemble
    IF --> AGG
    LSTM --> AGG
    OCSVM --> AGG
    AGG --> THRESH
    THRESH --> CLASS
    CLASS --> DEDUP
    DEDUP --> ENRICH
    ENRICH --> KP
    KP --> KAFKA_OUT["Kafka<br/>ics.anomalies"]

    style IF fill:#e63946,color:#fff
    style LSTM fill:#e63946,color:#fff
    style OCSVM fill:#e63946,color:#fff
```

### Component Responsibilities

#### Input Layer

| Component       | Responsibility          | Key Logic                                 |
| --------------- | ----------------------- | ----------------------------------------- |
| Kafka Consumer  | Consume feature vectors | Batch consumption (100 msgs), auto-commit |
| Input Validator | Validate feature schema | JSON Schema validation, null handling     |
| Normalizer      | Scale features          | Z-score normalization using stored stats  |

#### Model Layer

| Component        | Responsibility             | Key Logic                                 |
| ---------------- | -------------------------- | ----------------------------------------- |
| Model Loader     | Load models from registry  | ONNX format, warm-up inference            |
| Model Cache      | Keep models in memory      | LRU cache, version tracking               |
| Isolation Forest | Point anomaly detection    | Ensemble of 100 trees, contamination=0.01 |
| LSTM-AE          | Sequence anomaly detection | 2-layer LSTM, reconstruction error        |
| One-Class SVM    | Boundary-based detection   | RBF kernel, nu=0.01                       |

#### Scoring Layer

| Component        | Responsibility       | Key Logic                               |
| ---------------- | -------------------- | --------------------------------------- |
| Score Aggregator | Combine model scores | Weighted average (configurable weights) |
| Threshold Engine | Dynamic thresholding | Per-device, time-of-day adaptive        |
| Classifier       | Label anomaly type   | Rule-based + learned patterns           |

**Anomaly Type Classification:**

```mermaid
flowchart LR
    SCORE["Anomaly Score"] --> RULES["Rule Engine"]

    subgraph Types["Anomaly Types"]
        T1["RECONNAISSANCE<br/><i>Scan patterns</i>"]
        T2["PROTOCOL_VIOLATION<br/><i>Invalid commands</i>"]
        T3["VALUE_MANIPULATION<br/><i>Abnormal values</i>"]
        T4["TIMING_ANOMALY<br/><i>Unusual timing</i>"]
        T5["UNKNOWN<br/><i>Unclassified</i>"]
    end

    RULES --> Types
```

#### Output Layer

| Component      | Responsibility            | Key Logic                           |
| -------------- | ------------------------- | ----------------------------------- |
| Deduplicator   | Suppress duplicate alerts | Time window (5min), similarity hash |
| Enricher       | Add contextual data       | Device info, historical baseline    |
| Kafka Producer | Publish to alert topic    | Async batched writes                |

---

## Feature Engine Components

```mermaid
flowchart TB
    subgraph FeatureEngine["Feature Engine"]
        subgraph Ingestion["Ingestion"]
            KC["Kafka Consumer<br/><i>Multi-topic</i>"]
            ROUTE["Protocol Router<br/><i>Dispatch by type</i>"]
        end

        subgraph Windows["Window Management"]
            WM["Window Manager<br/><i>Tumbling windows</i>"]
            BUF["Event Buffer<br/><i>Per-window storage</i>"]
        end

        subgraph Extraction["Feature Extraction"]
            subgraph Extractors["Protocol Extractors"]
                MOD["Modbus Extractor"]
                DNP["DNP3 Extractor"]
                OPC["OPC-UA Extractor"]
            end

            subgraph Aggregators["Aggregators"]
                VOL["Volume Stats<br/><i>count, bytes, unique</i>"]
                TIME["Timing Stats<br/><i>IAT, jitter, bursts</i>"]
                PROTO["Protocol Stats<br/><i>function codes, errors</i>"]
                NET["Network Stats<br/><i>topology, fan-out</i>"]
            end
        end

        subgraph Output["Output"]
            VEC["Vector Builder<br/><i>Flatten to array</i>"]
            KP["Kafka Producer"]
        end
    end

    KAFKA["Kafka<br/>ics.raw.*"] --> KC
    KC --> ROUTE
    ROUTE --> WM
    WM --> BUF

    BUF --> MOD
    BUF --> DNP
    BUF --> OPC

    MOD --> VOL
    MOD --> TIME
    MOD --> PROTO
    DNP --> VOL
    DNP --> TIME
    DNP --> PROTO
    OPC --> VOL
    OPC --> TIME
    OPC --> PROTO

    VOL --> NET
    TIME --> NET
    PROTO --> NET

    NET --> VEC
    VEC --> KP
    KP --> KAFKA_OUT["Kafka<br/>ics.features"]
```

### Window Management Strategy

```mermaid
gantt
    title Feature Windows
    dateFormat X
    axisFormat %s

    section 1-minute
    Window 1  :0, 60
    Window 2  :60, 120
    Window 3  :120, 180

    section 5-minute
    Window 1  :0, 300
    Window 2  :300, 600

    section 15-minute
    Window 1  :0, 900
```

**Window Configuration:**

| Window    | Duration | Overlap | Use Case                |
| --------- | -------- | ------- | ----------------------- |
| 1-minute  | 60s      | 0%      | High-frequency patterns |
| 5-minute  | 300s     | 0%      | Medium-term trends      |
| 15-minute | 900s     | 0%      | Long-term baselines     |

### Feature Vector Structure

```typescript
interface FeatureVector {
  // Metadata
  timestamp: string
  window_end: string
  source_ip: string
  dest_ip: string
  protocol: string

  // Volume features (per window size)
  msg_count_1m: number
  msg_count_5m: number
  msg_count_15m: number
  bytes_total_1m: number
  bytes_total_5m: number
  unique_sources_5m: number

  // Timing features
  inter_arrival_mean_1m: number
  inter_arrival_std_1m: number
  inter_arrival_max_1m: number
  burst_score_1m: number

  // Protocol features (Modbus example)
  function_code_entropy_5m: number
  read_write_ratio_5m: number
  error_rate_5m: number
  new_register_addresses_5m: number

  // Network features
  unique_device_pairs_15m: number
  fan_out_ratio_15m: number
  scan_score_15m: number

  // Total: ~150 features
}
```

---

## Alert Manager Components

```mermaid
flowchart TB
    subgraph AlertManager["Alert Manager"]
        subgraph Ingestion["Ingestion"]
            KC["Kafka Consumer<br/><i>ics.anomalies</i>"]
        end

        subgraph Processing["Processing"]
            CORR["Correlator<br/><i>Group related</i>"]
            SEV["Severity Calculator<br/><i>Risk scoring</i>"]
            DEDUP["Deduplicator<br/><i>5-min window</i>"]
        end

        subgraph Enrichment["Enrichment"]
            ASSET["Asset Lookup<br/><i>Device context</i>"]
            HIST["History Lookup<br/><i>Prior alerts</i>"]
            MITRE["MITRE Mapper<br/><i>ATT&CK for ICS</i>"]
        end

        subgraph Dispatch["Dispatch"]
            STORE["Alert Store<br/><i>PostgreSQL</i>"]
            NOTIFY["Notifier<br/><i>Webhooks, email</i>"]
            SIEM["SIEM Forwarder<br/><i>CEF format</i>"]
        end
    end

    KAFKA["Kafka<br/>ics.anomalies"] --> KC
    KC --> CORR
    CORR --> SEV
    SEV --> DEDUP
    DEDUP --> ASSET
    ASSET --> HIST
    HIST --> MITRE
    MITRE --> STORE
    MITRE --> NOTIFY
    MITRE --> SIEM

    STORE --> PG["PostgreSQL"]
    SIEM --> EXT_SIEM["External SIEM"]
```

### Severity Calculation

```mermaid
flowchart LR
    subgraph Inputs["Severity Inputs"]
        AS["Anomaly Score<br/>(0-1)"]
        AI["Asset Importance<br/>(1-5)"]
        AT["Anomaly Type<br/>(weighted)"]
        RP["Repeat Penalty<br/>(if recurring)"]
    end

    CALC["Severity Calculator<br/><i>weighted formula</i>"]

    subgraph Output["Output"]
        SEV["Severity Level"]
        CRIT["CRITICAL<br/>> 0.9"]
        HIGH["HIGH<br/>0.7 - 0.9"]
        MED["MEDIUM<br/>0.4 - 0.7"]
        LOW["LOW<br/>< 0.4"]
    end

    Inputs --> CALC
    CALC --> SEV
    SEV --> CRIT
    SEV --> HIGH
    SEV --> MED
    SEV --> LOW
```

**Severity Formula:**

```
severity = (anomaly_score * 0.4) +
           (asset_importance / 5 * 0.3) +
           (type_weight * 0.2) +
           (repeat_penalty * 0.1)
```

### MITRE ATT&CK for ICS Mapping

| Anomaly Type       | MITRE Technique                          |
| ------------------ | ---------------------------------------- |
| RECONNAISSANCE     | T0846 - Remote System Discovery          |
| PROTOCOL_VIOLATION | T0855 - Unauthorized Command Message     |
| VALUE_MANIPULATION | T0879 - Damage to Property               |
| TIMING_ANOMALY     | T0882 - Theft of Operational Information |
