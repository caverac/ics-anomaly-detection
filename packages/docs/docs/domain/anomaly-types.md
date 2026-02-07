---
sidebar_position: 3
---

# Anomaly Types

The system classifies detected anomalies into distinct categories for actionable alerting.

## Anomaly Classification

```mermaid
flowchart TB
    SCORE["Anomaly Score<br/>(from ML models)"]

    subgraph Classification["Classification Engine"]
        RULES["Rule-Based Classifier"]
        LEARNED["Learned Patterns"]
    end

    subgraph Types["Anomaly Types"]
        RECON["RECONNAISSANCE"]
        PROTO["PROTOCOL_VIOLATION"]
        VALUE["VALUE_MANIPULATION"]
        TIMING["TIMING_ANOMALY"]
        TOPOLOGY["TOPOLOGY_CHANGE"]
        UNKNOWN["UNKNOWN"]
    end

    SCORE --> Classification
    Classification --> Types

    style RECON fill:#e63946,color:#fff
    style PROTO fill:#f4a261,color:#000
    style VALUE fill:#e9c46a,color:#000
    style TIMING fill:#2a9d8f,color:#fff
    style TOPOLOGY fill:#457b9d,color:#fff
    style UNKNOWN fill:#6c757d,color:#fff
```

## Type: RECONNAISSANCE

**Description:** Scanning or enumeration activity targeting ICS devices.

**Indicators:**
- High number of unique destination IPs from single source
- Sequential address scanning
- Failed connection attempts
- Probing of multiple protocols/ports

**MITRE Mapping:** T0846 (Remote System Discovery)

```mermaid
sequenceDiagram
    participant ATK as Attacker
    participant PLC1 as PLC 1
    participant PLC2 as PLC 2
    participant PLC3 as PLC 3

    ATK->>PLC1: Read Device ID (FC 43)
    PLC1-->>ATK: Response
    ATK->>PLC2: Read Device ID (FC 43)
    PLC2-->>ATK: Response
    ATK->>PLC3: Read Device ID (FC 43)
    PLC3-->>ATK: Response

    Note over ATK,PLC3: Sequential enumeration<br/>triggers RECONNAISSANCE alert
```

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `unique_destinations_5m` | 2-5 | > 20 |
| `scan_score_15m` | < 0.1 | > 0.7 |
| `failed_connections_5m` | 0-2 | > 10 |

---

## Type: PROTOCOL_VIOLATION

**Description:** Traffic that violates ICS protocol specifications.

**Indicators:**
- Invalid function codes
- Malformed packet structure
- Unexpected response codes
- Protocol state violations

**MITRE Mapping:** T0855 (Unauthorized Command Message)

```mermaid
sequenceDiagram
    participant ATK as Attacker
    participant PLC as PLC

    ATK->>PLC: Function Code 99 (Invalid)
    PLC-->>ATK: Exception: Illegal Function

    ATK->>PLC: Read Registers (malformed length)
    PLC-->>ATK: Exception: Illegal Data Value

    Note over ATK,PLC: Invalid commands<br/>trigger PROTOCOL_VIOLATION
```

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `error_rate_5m` | < 1% | > 10% |
| `invalid_function_codes` | 0 | > 0 |
| `exception_responses_5m` | < 2 | > 10 |

---

## Type: VALUE_MANIPULATION

**Description:** Process values outside expected ranges or changing abnormally.

**Indicators:**
- Values outside historical bounds
- Sudden large changes in setpoints
- Oscillating values
- Values inconsistent with physical constraints

**MITRE Mapping:** T0831 (Manipulation of Control)

```mermaid
xychart-beta
    title "Temperature Sensor - Normal vs Attack"
    x-axis ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    y-axis "Temperature (°C)" 0 --> 150
    line "Normal" [70, 71, 69, 70, 72, 71, 70, 69, 71, 70, 70]
    line "Attack" [70, 71, 69, 120, 45, 150, 30, 140, 50, 130, 60]
```

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `value_change_rate_1m` | < 5% | > 50% |
| `out_of_range_values_5m` | 0 | > 3 |
| `value_entropy_5m` | Low | High |

---

## Type: TIMING_ANOMALY

**Description:** Deviations from expected communication timing patterns.

**Indicators:**
- Inter-arrival time deviation
- Missing expected polls
- Burst traffic patterns
- Communication outside scheduled windows

**MITRE Mapping:** T0882 (Theft of Operational Information)

```mermaid
xychart-beta
    title "Inter-Arrival Time Distribution"
    x-axis ["Normal", "Burst", "Missing", "Irregular"]
    y-axis "Frequency"
    bar [100, 5, 2, 8]
```

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `inter_arrival_std_1m` | < 10ms | > 100ms |
| `burst_score_1m` | < 0.2 | > 0.8 |
| `missed_polls_5m` | 0 | > 5 |

---

## Type: TOPOLOGY_CHANGE

**Description:** New or unexpected communication relationships.

**Indicators:**
- New source-destination pairs
- Communication from unexpected subnets
- New protocols on existing pairs
- Changes in communication direction

**MITRE Mapping:** T0846 (Remote System Discovery), Lateral Movement

```mermaid
flowchart LR
    subgraph Before["Normal Topology"]
        H1["HMI"] --> P1["PLC 1"]
        H1 --> P2["PLC 2"]
    end

    subgraph After["Anomalous Topology"]
        H2["HMI"] --> P3["PLC 1"]
        H2 --> P4["PLC 2"]
        X["Unknown"] -->|"New!"| P3
        P3 -->|"New!"| P4
    end

    style X fill:#e63946,color:#fff
```

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `new_source_ips_15m` | 0 | > 0 |
| `new_pairs_15m` | 0 | > 0 |
| `topology_delta_score` | 0 | > 0.5 |

---

## Type: UNKNOWN

**Description:** Anomalous behavior that doesn't match known patterns.

**When Used:**
- High anomaly score from ML models
- No rule-based classification matches
- Potentially novel attack technique

**Action Required:**
- Manual investigation
- Possible model retraining opportunity

---

## Severity Mapping

| Type | Default Severity | Rationale |
|------|-----------------|-----------|
| PROTOCOL_VIOLATION | Critical | Indicates active attack or misconfiguration |
| VALUE_MANIPULATION | Critical | Direct process impact |
| RECONNAISSANCE | High | Precursor to attack |
| TOPOLOGY_CHANGE | High | Potential lateral movement |
| TIMING_ANOMALY | Medium | May indicate issues or collection |
| UNKNOWN | Medium | Requires investigation |

## Classification Decision Tree

```mermaid
flowchart TB
    START["Anomaly Detected"]

    Q1{"Protocol error<br/>or invalid command?"}
    Q2{"New device or<br/>communication pair?"}
    Q3{"Value outside<br/>expected range?"}
    Q4{"Timing deviation<br/>detected?"}
    Q5{"Scan-like<br/>behavior?"}

    A1["PROTOCOL_VIOLATION"]
    A2["TOPOLOGY_CHANGE"]
    A3["VALUE_MANIPULATION"]
    A4["TIMING_ANOMALY"]
    A5["RECONNAISSANCE"]
    A6["UNKNOWN"]

    START --> Q1
    Q1 -->|Yes| A1
    Q1 -->|No| Q2
    Q2 -->|Yes| A2
    Q2 -->|No| Q3
    Q3 -->|Yes| A3
    Q3 -->|No| Q4
    Q4 -->|Yes| A4
    Q4 -->|No| Q5
    Q5 -->|Yes| A5
    Q5 -->|No| A6

    style A1 fill:#e63946,color:#fff
    style A2 fill:#457b9d,color:#fff
    style A3 fill:#e9c46a,color:#000
    style A4 fill:#2a9d8f,color:#fff
    style A5 fill:#f4a261,color:#000
    style A6 fill:#6c757d,color:#fff
```
