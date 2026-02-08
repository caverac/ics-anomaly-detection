---
sidebar_position: 5
---

# Deployment Architecture

This page describes the deployment topology and infrastructure requirements.

## Deployment Options

The system supports three deployment models:

```mermaid
flowchart TB
    subgraph Options["Deployment Options"]
        subgraph Dev["Development"]
            D1["Docker Compose<br/><i>Single machine</i>"]
        end

        subgraph Edge["Edge Deployment"]
            E1["Kubernetes (K3s)<br/><i>On-premise</i>"]
        end

        subgraph Cloud["Cloud Deployment"]
            C1["Kubernetes (EKS/GKE)<br/><i>Managed cloud</i>"]
        end
    end

    style Dev fill:#2a9d8f,color:#fff
    style Edge fill:#e9c46a,color:#000
    style Cloud fill:#457b9d,color:#fff
```

---

## Development Environment

Single-machine deployment for local development and testing.

```mermaid
flowchart TB
    subgraph Docker["Docker Compose"]
        subgraph Services["Core Services"]
            SIM["simulator"]
            PARSE["parser"]
            FEAT["feature-engine"]
            INF["anomaly-detection"]
            ALERT["alerting"]
            DASH["dashboard"]
        end

        subgraph Infra["Infrastructure"]
            KAFKA["kafka (KRaft)"]
            REDIS["redis"]
        end

        subgraph Monitoring["Monitoring"]
            PROM["prometheus"]
            GRAF["grafana"]
        end
    end

    SIM -->|"ics.raw.packets"| KAFKA
    KAFKA --> PARSE
    PARSE --> KAFKA
    KAFKA --> FEAT
    FEAT --> KAFKA
    KAFKA --> INF
    INF --> KAFKA
    KAFKA --> ALERT
    ALERT --> REDIS
    DASH --> ALERT
    PROM --> GRAF

    style SIM fill:#f4a261,color:#000
```

**Resource Requirements (Development):**

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Kafka (KRaft) | 1 core | 1 GB | 10 GB |
| Redis | 0.5 core | 256 MB | 1 GB |
| Simulator | 0.5 core | 256 MB | - |
| Parser | 1 core | 512 MB | - |
| Feature Engine | 0.5 core | 512 MB | - |
| Anomaly Detection | 1 core | 1 GB | - |
| Alerting | 0.5 core | 256 MB | - |
| Dashboard | 0.5 core | 256 MB | - |
| **Total** | **~6 cores** | **~5 GB** | **11 GB** |

---

## Edge Deployment (On-Premise)

Production deployment at customer site, optimized for resource constraints.

```mermaid
flowchart TB
    subgraph Network["Customer ICS Network"]
        PLC1["PLC/RTU"]
        PLC2["PLC/RTU"]
        HMI["HMI"]
        SW["Network Switch"]
    end

    subgraph TAP["Network TAP"]
        SPAN["SPAN Port"]
    end

    subgraph Edge["Edge Appliance (K3s Cluster)"]
        subgraph Node1["Node 1 - Ingestion"]
            CAP["packet-capture<br/><i>DaemonSet</i>"]
            PARSE["protocol-parser"]
        end

        subgraph Node2["Node 2 - Processing"]
            KAFKA["Kafka (KRaft)"]
            FEAT["feature-engine"]
            INF["inference-service"]
        end

        subgraph Node3["Node 3 - Storage & UI"]
            TS["TimescaleDB"]
            PG["PostgreSQL"]
            API["rest-api"]
            DASH["dashboard"]
            ALERT["alert-manager"]
        end

        subgraph Shared["Shared Services"]
            PROM["Prometheus"]
            REDIS["Redis"]
        end
    end

    subgraph External["External Integration"]
        SIEM["Customer SIEM"]
        NTP["NTP Server"]
    end

    PLC1 --> SW
    PLC2 --> SW
    HMI --> SW
    SW --> SPAN
    SPAN --> CAP

    CAP --> PARSE
    PARSE --> KAFKA
    KAFKA --> FEAT
    KAFKA --> INF
    INF --> ALERT
    ALERT --> PG
    ALERT --> SIEM
    FEAT --> TS
    API --> PG
    DASH --> API

    NTP -.-> Edge

    style Node1 fill:#1d3557,color:#fff
    style Node2 fill:#e63946,color:#fff
    style Node3 fill:#457b9d,color:#fff
```

**Edge Hardware Specification:**

| Node | Role | CPU | Memory | Storage | NIC |
|------|------|-----|--------|---------|-----|
| Node 1 | Ingestion | 4 cores | 8 GB | 100 GB SSD | 10 GbE (capture) |
| Node 2 | Processing | 8 cores | 32 GB | 500 GB NVMe | 1 GbE |
| Node 3 | Storage/UI | 4 cores | 16 GB | 1 TB SSD | 1 GbE |

**Network Segmentation:**

```mermaid
flowchart LR
    subgraph OT["OT Network (Level 1-2)"]
        PLC["PLCs/RTUs"]
        HMI["HMIs"]
    end

    subgraph DMZ["ICS DMZ (Level 3)"]
        TAP["Network TAP"]
        EDGE["Edge Appliance"]
    end

    subgraph IT["IT Network (Level 4)"]
        SIEM["SIEM"]
        SOC["SOC Workstations"]
    end

    OT -->|"Mirrored traffic<br/>(one-way)"| TAP
    TAP --> EDGE
    EDGE -->|"Alerts only<br/>(firewall)"| IT
    SOC -->|"Dashboard access<br/>(HTTPS only)"| EDGE

    style OT fill:#e63946,color:#fff
    style DMZ fill:#f4a261,color:#000
    style IT fill:#2a9d8f,color:#fff
```

---

## Cloud Deployment

Managed Kubernetes deployment for cloud-based or hybrid scenarios.

```mermaid
flowchart TB
    subgraph VPC["AWS VPC"]
        subgraph Public["Public Subnet"]
            ALB["Application Load Balancer"]
            NAT["NAT Gateway"]
        end

        subgraph Private["Private Subnet"]
            subgraph EKS["EKS Cluster"]
                subgraph Ingestion["Ingestion Node Group"]
                    CAP["packet-capture<br/><i>c5n.xlarge</i>"]
                    PARSE["protocol-parser"]
                end

                subgraph Compute["Compute Node Group"]
                    FEAT["feature-engine<br/><i>HPA: 2-10</i>"]
                    INF["inference-service<br/><i>HPA: 2-10</i>"]
                    ALERT["alert-manager"]
                end

                subgraph API_NG["API Node Group"]
                    API["rest-api<br/><i>HPA: 2-5</i>"]
                    DASH["dashboard"]
                end
            end

            subgraph Managed["Managed Services"]
                MSK["Amazon MSK<br/><i>Kafka</i>"]
                RDS["Amazon RDS<br/><i>PostgreSQL</i>"]
                TSDB["TimescaleDB<br/><i>EC2/RDS</i>"]
                ELAST["ElastiCache<br/><i>Redis</i>"]
            end
        end
    end

    subgraph OnPrem["On-Premise"]
        COLLECTOR["Traffic Collector<br/><i>VPN tunnel</i>"]
    end

    subgraph Users["Users"]
        SOC["SOC Analysts"]
    end

    COLLECTOR -->|"VPN"| CAP
    CAP --> PARSE
    PARSE --> MSK
    MSK --> FEAT
    MSK --> INF
    INF --> ALERT
    ALERT --> RDS
    FEAT --> TSDB
    API --> RDS
    API --> ELAST

    SOC --> ALB
    ALB --> API
    ALB --> DASH

    style MSK fill:#ff9900,color:#000
    style RDS fill:#ff9900,color:#000
    style ELAST fill:#ff9900,color:#000
```

**AWS Resource Sizing:**

| Service | Instance/Size | Quantity | Purpose |
|---------|--------------|----------|---------|
| EKS | Managed | 1 cluster | Container orchestration |
| EC2 (Ingestion) | c5n.xlarge | 2 | High-network capture |
| EC2 (Compute) | c5.2xlarge | 2-10 | ML inference |
| EC2 (API) | t3.large | 2-5 | API serving |
| MSK | kafka.m5.large | 3 brokers | Event streaming |
| RDS | db.r5.large | 1 (Multi-AZ) | Alert storage |
| TimescaleDB | i3.xlarge | 1 | Time-series |
| ElastiCache | cache.r5.large | 1 | Caching |

---

## Kubernetes Resources

### Namespace Structure

```mermaid
flowchart TB
    subgraph Cluster["Kubernetes Cluster"]
        subgraph NS1["ics-ingestion"]
            CAP["packet-capture"]
            PARSE["protocol-parser"]
        end

        subgraph NS2["ics-processing"]
            FEAT["feature-engine"]
            INF["inference-service"]
        end

        subgraph NS3["ics-alerting"]
            ALERT["alert-manager"]
        end

        subgraph NS4["ics-api"]
            API["rest-api"]
            DASH["dashboard"]
        end

        subgraph NS5["ics-infra"]
            KAFKA["kafka"]
            PG["postgresql"]
            TS["timescaledb"]
            REDIS["redis"]
        end

        subgraph NS6["ics-monitoring"]
            PROM["prometheus"]
            GRAF["grafana"]
            LOKI["loki"]
        end
    end
```

### Resource Quotas

```yaml
# Per-namespace resource quotas
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ics-processing-quota
  namespace: ics-processing
spec:
  hard:
    requests.cpu: "16"
    requests.memory: "64Gi"
    limits.cpu: "32"
    limits.memory: "128Gi"
    pods: "20"
```

### Horizontal Pod Autoscaler

```mermaid
flowchart LR
    subgraph HPA["HPA Configuration"]
        FEAT_HPA["feature-engine<br/>min: 2, max: 10<br/>target CPU: 70%"]
        INF_HPA["inference-service<br/>min: 2, max: 10<br/>target CPU: 60%"]
        API_HPA["rest-api<br/>min: 2, max: 5<br/>target CPU: 70%"]
    end

    PROM["Prometheus<br/>Metrics"] --> HPA
    HPA --> SCALE["Scale Pods"]
```

---

## Observability Stack

```mermaid
flowchart TB
    subgraph Apps["Applications"]
        SVC1["packet-capture"]
        SVC2["protocol-parser"]
        SVC3["feature-engine"]
        SVC4["inference-service"]
        SVC5["alert-manager"]
        SVC6["rest-api"]
    end

    subgraph Collection["Collection"]
        PROM["Prometheus<br/><i>Metrics</i>"]
        LOKI["Loki<br/><i>Logs</i>"]
        TEMPO["Tempo<br/><i>Traces</i>"]
    end

    subgraph Visualization["Visualization"]
        GRAF["Grafana<br/><i>Dashboards</i>"]
    end

    subgraph Alerting["Alerting"]
        AM["Alertmanager"]
        PD["PagerDuty"]
        SLACK["Slack"]
    end

    Apps -->|"/metrics"| PROM
    Apps -->|"stdout/stderr"| LOKI
    Apps -->|"OpenTelemetry"| TEMPO

    PROM --> GRAF
    LOKI --> GRAF
    TEMPO --> GRAF

    PROM --> AM
    AM --> PD
    AM --> SLACK

    style PROM fill:#e6522c,color:#fff
    style GRAF fill:#f46800,color:#fff
    style LOKI fill:#f46800,color:#fff
```

**Key Metrics:**

| Category | Metric | Alert Threshold |
|----------|--------|-----------------|
| Ingestion | `packets_captured_total` | Drop > 0.1% |
| Ingestion | `parse_errors_total` | > 100/min |
| Processing | `feature_extraction_latency_p99` | > 1s |
| ML | `inference_latency_p99` | > 50ms |
| ML | `model_prediction_errors` | > 10/min |
| Alerting | `alerts_generated_total` | Anomaly spike |
| API | `http_request_duration_p99` | > 500ms |

---

## Disaster Recovery

```mermaid
flowchart TB
    subgraph Primary["Primary Site"]
        P_EDGE["Edge Appliance"]
        P_KAFKA["Kafka"]
        P_DB["Databases"]
    end

    subgraph Backup["Backup Strategy"]
        S3["S3 Bucket<br/><i>Daily snapshots</i>"]
        MODELS["Model Registry<br/><i>Versioned models</i>"]
        CONFIG["Config Backup<br/><i>GitOps</i>"]
    end

    subgraph DR["Disaster Recovery"]
        DR_EDGE["Standby Appliance<br/><i>Cold standby</i>"]
    end

    P_DB -->|"pg_dump daily"| S3
    P_KAFKA -->|"Topic backup"| S3
    P_EDGE -->|"Models"| MODELS
    P_EDGE -->|"Configs"| CONFIG

    S3 -.->|"Restore"| DR_EDGE
    MODELS -.->|"Restore"| DR_EDGE
    CONFIG -.->|"Restore"| DR_EDGE
```

**Recovery Objectives:**

| Metric | Target | Strategy |
|--------|--------|----------|
| RPO (Recovery Point Objective) | 1 hour | Hourly Kafka topic backup |
| RTO (Recovery Time Objective) | 4 hours | Cold standby + automated restore |
| Model Recovery | 15 minutes | Model registry with versioning |
| Config Recovery | 5 minutes | GitOps (ArgoCD) |
