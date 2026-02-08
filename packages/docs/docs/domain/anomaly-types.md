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
        FEATURES["Feature Contributions"]
    end

    subgraph Types["Anomaly Types"]
        RECON["RECONNAISSANCE"]
        TIMING["TIMING_ANOMALY"]
        VOLUME["VOLUME_ANOMALY"]
        PROTO["PROTOCOL_VIOLATION"]
        UNAUTH["UNAUTHORIZED_ACCESS"]
        EXFIL["DATA_EXFILTRATION"]
        INJECT["COMMAND_INJECTION"]
        UNKNOWN["UNKNOWN"]
    end

    SCORE --> Classification
    Classification --> Types

    style RECON fill:#e63946,color:#fff
    style PROTO fill:#f4a261,color:#000
    style INJECT fill:#e9c46a,color:#000
    style TIMING fill:#2a9d8f,color:#fff
    style VOLUME fill:#457b9d,color:#fff
    style UNKNOWN fill:#6c757d,color:#fff
```

## Type: RECONNAISSANCE

**Description:** Scanning or enumeration activity targeting ICS devices.

**Indicators:**

- High number of unique destination IPs from single source
- Sequential address scanning
- Device ID requests (Modbus FC 43)
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
| `fc_unique_count` | 2-4 | > 10 |
| `addr_range` | < 100 | > 1000 |
| `fc_diagnostic_ratio` | < 0.1 | > 0.5 |

---

## Type: TIMING_ANOMALY

**Description:** Deviations from expected communication timing patterns.

**Indicators:**

- Inter-arrival time deviation
- Missing expected polls
- Burst traffic patterns
- Irregular request spacing

**MITRE Mapping:** T0882 (Theft of Operational Information)

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `iat_std` | < 0.1s | > 1.0s |
| `iat_max` | < 2s | > 10s |
| `message_count` deviation | < 10% | > 50% |

---

## Type: VOLUME_ANOMALY

**Description:** Abnormal traffic volume compared to baseline.

**Indicators:**

- Significantly higher message count than normal
- Unusually large payload sizes
- Traffic spikes or drops

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `message_count` | baseline ± 10% | > 2x baseline |
| `bytes_total` | baseline ± 20% | > 3x baseline |
| `bytes_max` | < 256 | > 1024 |

---

## Type: PROTOCOL_VIOLATION

**Description:** Traffic that violates ICS protocol specifications.

**Indicators:**

- Invalid function codes
- Malformed packet structure
- Unexpected response codes
- Exception responses

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
| `exception_ratio` | < 1% | > 10% |
| `exception_count` | 0-2 | > 10 |
| `fc_entropy` | Low | Very high |

---

## Type: UNAUTHORIZED_ACCESS

**Description:** Access to restricted or unusual register addresses.

**Indicators:**

- Access to addresses outside normal range
- New address patterns not seen in baseline
- Access to configuration registers

**MITRE Mapping:** T0821 (Modify Controller Tasking)

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `addr_unique_count` | < 20 | > 100 |
| `addr_range` | consistent | expanded |
| `unit_id_unique_count` | 1-3 | > 10 |

---

## Type: DATA_EXFILTRATION

**Description:** Unusual data extraction patterns indicating information theft.

**Indicators:**

- Large number of read operations
- Sequential register reads
- High data volume extraction
- Unusual read patterns

**MITRE Mapping:** T0882 (Theft of Operational Information)

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `fc_read_ratio` | balanced | > 0.95 |
| `qty_mean` | < 10 | > 50 |
| `bytes_total` | normal | very high |

---

## Type: COMMAND_INJECTION

**Description:** Unauthorized write operations or malicious commands.

**Indicators:**

- Unexpected write commands
- Write operations from new sources
- Dangerous function codes
- Unusual write patterns

**MITRE Mapping:** T0831 (Manipulation of Control)

```mermaid
sequenceDiagram
    participant ATK as Attacker
    participant PLC as PLC

    ATK->>PLC: Write Single Register (FC 06)<br/>Address: 100, Value: 9999

    ATK->>PLC: Write Multiple Registers (FC 16)<br/>Address: 200, Values: [0,0,0,0]

    Note over ATK,PLC: Unauthorized writes<br/>trigger COMMAND_INJECTION
```

**Detection Features:**
| Feature | Normal | Anomalous |
|---------|--------|-----------|
| `fc_write_ratio` | < 0.2 | > 0.5 |
| `request_ratio` deviation | stable | sudden change |
| New write addresses | 0 | > 0 |

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

| Type                | Default Severity | Rationale                       |
| ------------------- | ---------------- | ------------------------------- |
| COMMAND_INJECTION   | Critical         | Direct process impact           |
| PROTOCOL_VIOLATION  | Critical         | Indicates active attack         |
| UNAUTHORIZED_ACCESS | High             | Potential reconnaissance/attack |
| DATA_EXFILTRATION   | High             | Information theft               |
| RECONNAISSANCE      | High             | Precursor to attack             |
| VOLUME_ANOMALY      | Medium           | May indicate issues             |
| TIMING_ANOMALY      | Medium           | May indicate collection         |
| UNKNOWN             | Medium           | Requires investigation          |

## Classification Decision Tree

```mermaid
flowchart TB
    START["Anomaly Detected"]

    Q1{"High write<br/>ratio?"}
    Q2{"Protocol errors<br/>or exceptions?"}
    Q3{"Unusual address<br/>patterns?"}
    Q4{"High read ratio<br/>+ volume?"}
    Q5{"Scan-like<br/>behavior?"}
    Q6{"Volume<br/>deviation?"}
    Q7{"Timing<br/>deviation?"}

    A1["COMMAND_INJECTION"]
    A2["PROTOCOL_VIOLATION"]
    A3["UNAUTHORIZED_ACCESS"]
    A4["DATA_EXFILTRATION"]
    A5["RECONNAISSANCE"]
    A6["VOLUME_ANOMALY"]
    A7["TIMING_ANOMALY"]
    A8["UNKNOWN"]

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
    Q5 -->|No| Q6
    Q6 -->|Yes| A6
    Q6 -->|No| Q7
    Q7 -->|Yes| A7
    Q7 -->|No| A8

    style A1 fill:#e63946,color:#fff
    style A2 fill:#f4a261,color:#000
    style A3 fill:#e9c46a,color:#000
    style A4 fill:#457b9d,color:#fff
    style A5 fill:#f4a261,color:#000
    style A6 fill:#2a9d8f,color:#fff
    style A7 fill:#2a9d8f,color:#fff
    style A8 fill:#6c757d,color:#fff
```
