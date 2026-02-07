---
sidebar_position: 1
---

# System Context

The System Context diagram shows the ICS Anomaly Detection Engine and its relationships with external systems and users.

## Context Diagram

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ICS["🏭 ICS/SCADA Network<br/><i>Modbus, DNP3, OPC-UA traffic</i>"]
        SIEM["📊 SIEM<br/><i>Splunk, Elastic, etc.</i>"]
        TICKET["🎫 Ticketing System<br/><i>ServiceNow, Jira</i>"]
    end

    subgraph Users["Users"]
        SOC["👤 SOC Analyst<br/><i>Monitors alerts, investigates incidents</i>"]
        ENG["👤 ML Engineer<br/><i>Trains models, tunes thresholds</i>"]
        OPS["👤 OT Operator<br/><i>Validates alerts, provides context</i>"]
    end

    subgraph System["ICS Anomaly Detection Engine"]
        CORE["🔍 Detection Engine<br/><i>Real-time anomaly detection<br/>for ICS network traffic</i>"]
    end

    ICS -->|"Network traffic<br/>(mirrored)"| CORE
    CORE -->|"Alerts, events"| SIEM
    CORE -->|"Incidents"| TICKET

    SOC -->|"View alerts<br/>Investigate"| CORE
    ENG -->|"Train models<br/>Configure"| CORE
    OPS -->|"Validate<br/>Feedback"| CORE

    style CORE fill:#e63946,color:#fff
    style ICS fill:#457b9d,color:#fff
    style SIEM fill:#2a9d8f,color:#fff
    style TICKET fill:#2a9d8f,color:#fff
```

## System Boundaries

### In Scope

| Component | Description |
|-----------|-------------|
| Traffic Capture | Passive network monitoring via SPAN/TAP |
| Protocol Parsing | Modbus TCP, DNP3, OPC-UA, Ethernet/IP |
| Feature Extraction | Time-series features from parsed traffic |
| Anomaly Detection | ML-based detection (unsupervised + supervised) |
| Alert Generation | Severity classification and deduplication |
| Dashboard | Real-time visualization and investigation |
| API | Programmatic access for integrations |

### Out of Scope

| Component | Reason |
|-----------|--------|
| Active response | This is a detection system, not prevention |
| Inline deployment | Passive monitoring only (safety-critical) |
| Asset inventory | Assumes asset data from existing CMDB |
| Vulnerability scanning | Separate concern, different tooling |

## External System Interactions

### ICS/SCADA Network (Data Source)

```mermaid
sequenceDiagram
    participant PLC as PLC/RTU
    participant NET as Network Switch
    participant TAP as Network TAP
    participant DET as Detection Engine

    PLC->>NET: Modbus TCP traffic
    NET->>TAP: Mirrored traffic (SPAN)
    TAP->>DET: Passive capture
    Note over DET: No traffic modification<br/>No response injection
```

**Integration Method:** Passive network tap (SPAN port mirror)

**Data Format:** Raw packets (PCAP compatible)

**Protocols Supported:**
- Modbus TCP (port 502)
- DNP3 (port 20000)
- OPC-UA (port 4840)
- Ethernet/IP (port 44818)

### SIEM Integration

```mermaid
sequenceDiagram
    participant DET as Detection Engine
    participant KAFKA as Event Bus
    participant SIEM as SIEM Platform

    DET->>KAFKA: Publish alert event
    Note over KAFKA: CEF/LEEF format
    KAFKA->>SIEM: Consume events
    SIEM->>SIEM: Correlate with IT alerts
```

**Integration Method:** Event streaming (Kafka) or Syslog (UDP/TCP)

**Data Format:** CEF (Common Event Format) or JSON

**Alert Fields:**
- `timestamp` - Event time (UTC)
- `source_ip` - Origin device
- `dest_ip` - Target device
- `protocol` - ICS protocol detected
- `anomaly_type` - Classification
- `severity` - Critical/High/Medium/Low
- `confidence` - Model confidence score
- `raw_features` - Feature vector for investigation

## User Personas

### SOC Analyst

**Goals:**
- Quickly triage ICS-related alerts
- Investigate potential incidents
- Escalate confirmed threats to OT team

**Interactions:**
- Dashboard: Real-time alert feed
- Alert details: Context, related events
- Search: Historical queries

### ML Engineer

**Goals:**
- Improve model accuracy
- Reduce false positives
- Adapt to new threat patterns

**Interactions:**
- Training pipeline: Retrain models
- Metrics: Model performance monitoring
- Configuration: Threshold tuning

### OT Operator

**Goals:**
- Validate alerts in operational context
- Provide ground truth feedback
- Identify maintenance vs. attack

**Interactions:**
- Alert validation: Mark true/false positives
- Context: Add operational notes
- Exceptions: Whitelist known behaviors
