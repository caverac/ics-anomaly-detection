---
sidebar_position: 2
---

# ICS Threat Landscape

Understanding the threat landscape helps inform what anomalies to detect.

## Notable ICS Attacks

| Year | Attack | Target | Impact |
|------|--------|--------|--------|
| 2010 | Stuxnet | Iran nuclear | Centrifuge destruction |
| 2015 | BlackEnergy | Ukraine power | 230K without power |
| 2016 | Industroyer | Ukraine power | Automated grid attack |
| 2017 | Triton/TRISIS | Saudi plant | Safety system compromise |
| 2021 | Oldsmar | Florida water | Attempted poisoning |
| 2021 | Colonial Pipeline | US fuel | Pipeline shutdown |

## Attack Lifecycle

```mermaid
flowchart LR
    subgraph Stages["ICS Attack Stages"]
        R["Reconnaissance<br/><i>Network mapping</i>"]
        A["Access<br/><i>Initial foothold</i>"]
        D["Discovery<br/><i>ICS enumeration</i>"]
        L["Lateral<br/><i>Move to OT</i>"]
        C["Collection<br/><i>Learn process</i>"]
        I["Impact<br/><i>Execute attack</i>"]
    end

    R --> A --> D --> L --> C --> I

    style R fill:#457b9d,color:#fff
    style A fill:#457b9d,color:#fff
    style D fill:#e9c46a,color:#000
    style L fill:#e9c46a,color:#000
    style C fill:#f4a261,color:#000
    style I fill:#e63946,color:#fff
```

### Detection Opportunities

| Stage | Network Indicators | Our Detection |
|-------|-------------------|---------------|
| Reconnaissance | Port scans, device enumeration | Scan score feature |
| Discovery | Protocol probing, register reads | New function codes |
| Lateral Movement | IT→OT traffic patterns | Topology changes |
| Collection | Unusual read patterns | Read frequency anomaly |
| Impact | Write commands, setpoint changes | Value manipulation |

## MITRE ATT&CK for ICS

We map detections to the [MITRE ATT&CK for ICS](https://attack.mitre.org/techniques/ics/) framework.

### Relevant Techniques

```mermaid
flowchart TB
    subgraph Reconnaissance["Reconnaissance"]
        T0846["T0846<br/>Remote System Discovery"]
        T0842["T0842<br/>Network Sniffing"]
    end

    subgraph Collection["Collection"]
        T0801["T0801<br/>Monitor Process State"]
        T0861["T0861<br/>Point & Tag Identification"]
    end

    subgraph Execution["Execution"]
        T0855["T0855<br/>Unauthorized Command Message"]
        T0821["T0821<br/>Modify Controller Tasking"]
    end

    subgraph Impact["Impact"]
        T0831["T0831<br/>Manipulation of Control"]
        T0879["T0879<br/>Damage to Property"]
        T0882["T0882<br/>Theft of Operational Info"]
    end

    style Reconnaissance fill:#457b9d,color:#fff
    style Collection fill:#e9c46a,color:#000
    style Execution fill:#f4a261,color:#000
    style Impact fill:#e63946,color:#fff
```

### Detection Coverage Matrix

| Technique | ID | Detection Method | Confidence |
|-----------|------|------------------|------------|
| Remote System Discovery | T0846 | Scan pattern detection | High |
| Network Sniffing | T0842 | Passive (out of scope) | N/A |
| Monitor Process State | T0801 | Unusual read patterns | Medium |
| Point & Tag Identification | T0861 | Register enumeration | High |
| Unauthorized Command | T0855 | Invalid function codes | High |
| Modify Controller Tasking | T0821 | Program upload detection | High |
| Manipulation of Control | T0831 | Value anomaly detection | Medium |
| Damage to Property | T0879 | Process state deviation | Medium |

## Threat Actor Categories

### Nation-State

- **Motivation:** Espionage, sabotage, pre-positioning
- **Capability:** High (custom malware, zero-days)
- **Examples:** Stuxnet, Industroyer, Triton
- **Detection difficulty:** High (long dwell time, stealth)

### Cybercriminal

- **Motivation:** Financial gain (ransomware)
- **Capability:** Medium (commodity tools)
- **Examples:** Colonial Pipeline, JBS
- **Detection difficulty:** Medium (faster, noisier)

### Insider

- **Motivation:** Disgruntlement, sabotage
- **Capability:** Variable (legitimate access)
- **Examples:** Maroochy Shire sewage
- **Detection difficulty:** High (authorized user)

### Hacktivist

- **Motivation:** Political, attention
- **Capability:** Low-Medium
- **Examples:** Oldsmar water treatment
- **Detection difficulty:** Low (usually unsophisticated)

## Attack Vectors

```mermaid
flowchart TB
    subgraph Entry["Entry Points"]
        VPN["VPN<br/><i>Remote access</i>"]
        RDP["RDP<br/><i>Jump hosts</i>"]
        SUPPLY["Supply Chain<br/><i>Software updates</i>"]
        PHISH["Phishing<br/><i>Operator workstation</i>"]
        USB["USB<br/><i>Air-gap bridge</i>"]
        VENDOR["Vendor Access<br/><i>Maintenance</i>"]
    end

    subgraph Pivot["Pivot to OT"]
        SHARED["Shared Credentials"]
        DUAL["Dual-Homed Hosts"]
        HISTO["Historian/DMZ"]
    end

    subgraph Target["OT Targets"]
        HMI["HMI"]
        EWS["Engineering WS"]
        PLC["PLCs/RTUs"]
    end

    Entry --> Pivot --> Target

    style Entry fill:#457b9d,color:#fff
    style Pivot fill:#e9c46a,color:#000
    style Target fill:#e63946,color:#fff
```

## What We Can Detect

Our system focuses on **network-based** detection at the OT level:

### Detectable

| Category | Examples |
|----------|----------|
| Reconnaissance | Port scans, device enumeration, protocol probing |
| Protocol violations | Invalid function codes, malformed packets |
| Behavioral anomalies | Unusual timing, new communication pairs |
| Value manipulation | Out-of-range values, rapid changes |
| Command anomalies | Unexpected writes, dangerous commands |

### Not Detectable (Out of Scope)

| Category | Why |
|----------|-----|
| IT-side attacks | We monitor OT network only |
| Encrypted traffic | Can detect metadata but not content |
| Physical attacks | No sensor integration |
| Credential theft | No identity layer |
| Supply chain | Pre-deployment compromise |

## Adversary Emulation

For testing, we simulate these attack patterns:

```mermaid
flowchart LR
    subgraph Scenarios["Test Scenarios"]
        S1["Modbus Scanning<br/><i>Enumerate devices</i>"]
        S2["Register Fuzzing<br/><i>Invalid addresses</i>"]
        S3["Command Injection<br/><i>Write operations</i>"]
        S4["Replay Attack<br/><i>Captured traffic</i>"]
        S5["DoS<br/><i>Flood requests</i>"]
        S6["MitM<br/><i>Value modification</i>"]
    end
```

See [Attack Scenarios](/simulation/attack-scenarios) for implementation details.
