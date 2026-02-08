---
sidebar_position: 1
---

# ICS Fundamentals

Understanding Industrial Control Systems is essential for building effective anomaly detection.

## What is ICS?

Industrial Control Systems (ICS) are used to monitor and control industrial processes in sectors like:

- **Energy** - Power generation, transmission, distribution
- **Water** - Treatment plants, distribution systems
- **Manufacturing** - Assembly lines, process control
- **Oil & Gas** - Refineries, pipelines, drilling
- **Transportation** - Rail systems, traffic control

## ICS Architecture

```mermaid
flowchart TB
    subgraph Level5["Level 5: Enterprise"]
        ERP["ERP Systems"]
        EMAIL["Email/Web"]
    end

    subgraph Level4["Level 4: Site Business"]
        HIST["Historian"]
        MES["MES"]
    end

    subgraph Level3["Level 3: Site Operations"]
        SCADA["SCADA Server"]
        EWS["Engineering Workstation"]
    end

    subgraph Level2["Level 2: Area Control"]
        HMI["HMI"]
        DCS["DCS"]
    end

    subgraph Level1["Level 1: Basic Control"]
        PLC["PLC"]
        RTU["RTU"]
    end

    subgraph Level0["Level 0: Process"]
        SENSOR["Sensors"]
        ACTUATOR["Actuators"]
        MOTOR["Motors/Valves"]
    end

    Level5 <--> Level4
    Level4 <--> Level3
    Level3 <--> Level2
    Level2 <--> Level1
    Level1 <--> Level0

    style Level0 fill:#e63946,color:#fff
    style Level1 fill:#f4a261,color:#000
    style Level2 fill:#e9c46a,color:#000
    style Level3 fill:#2a9d8f,color:#fff
    style Level4 fill:#457b9d,color:#fff
    style Level5 fill:#1d3557,color:#fff
```

### Purdue Model Levels

| Level | Name            | Components         | Function                        |
| ----- | --------------- | ------------------ | ------------------------------- |
| 0     | Process         | Sensors, actuators | Physical world interaction      |
| 1     | Basic Control   | PLCs, RTUs         | Direct process control          |
| 2     | Area Control    | HMIs, DCS          | Operator interface, supervision |
| 3     | Site Operations | SCADA, EWS         | Site-wide monitoring            |
| 4     | Site Business   | Historian, MES     | Data analytics, scheduling      |
| 5     | Enterprise      | ERP, email         | Business systems                |

## Key Components

### PLC (Programmable Logic Controller)

```mermaid
flowchart LR
    subgraph PLC["PLC"]
        INPUT["Input Modules<br/><i>Digital/Analog</i>"]
        CPU["CPU<br/><i>Ladder logic</i>"]
        OUTPUT["Output Modules<br/><i>Digital/Analog</i>"]
        COMM["Communication<br/><i>Ethernet/Serial</i>"]
    end

    SENSOR["Sensors"] --> INPUT
    INPUT --> CPU
    CPU --> OUTPUT
    OUTPUT --> ACTUATOR["Actuators"]
    COMM <--> SCADA["SCADA/HMI"]
```

**Characteristics:**

- Deterministic execution (scan cycle)
- Real-time response (milliseconds)
- Designed for reliability (24/7 operation)
- Programmed in IEC 61131-3 languages

### RTU (Remote Terminal Unit)

Similar to PLCs but designed for:

- Remote/unmanned locations
- Wide-area communication (radio, cellular)
- Environmental hardening
- Battery backup operation

### HMI (Human-Machine Interface)

Operator interface providing:

- Process visualization
- Alarm management
- Setpoint adjustment
- Historical trending

### SCADA (Supervisory Control and Data Acquisition)

Central system for:

- Aggregating data from multiple PLCs/RTUs
- Providing enterprise-wide visibility
- Historical data storage
- Alarm correlation

## ICS Protocols

### Modbus TCP

The most common ICS protocol. Simple, request-response based.

```mermaid
sequenceDiagram
    participant M as Master (HMI)
    participant S as Slave (PLC)

    M->>S: Read Holding Registers (FC 03)<br/>Address: 100, Quantity: 10
    S->>M: Response: 10 register values

    M->>S: Write Single Register (FC 06)<br/>Address: 200, Value: 500
    S->>M: Response: Echo of write

    M->>S: Write Multiple Registers (FC 16)<br/>Address: 300, Values: [1,2,3,4]
    S->>M: Response: Quantity written
```

**Function Codes:**

| Code | Function                 | Type  |
| ---- | ------------------------ | ----- |
| 01   | Read Coils               | Read  |
| 02   | Read Discrete Inputs     | Read  |
| 03   | Read Holding Registers   | Read  |
| 04   | Read Input Registers     | Read  |
| 05   | Write Single Coil        | Write |
| 06   | Write Single Register    | Write |
| 15   | Write Multiple Coils     | Write |
| 16   | Write Multiple Registers | Write |

### DNP3 (Distributed Network Protocol)

Used primarily in electric and water utilities.

```mermaid
flowchart TB
    subgraph DNP3Stack["DNP3 Protocol Stack"]
        APP["Application Layer<br/><i>Objects, functions</i>"]
        TRANS["Transport Layer<br/><i>Fragmentation</i>"]
        LINK["Data Link Layer<br/><i>Framing, addressing</i>"]
        PHYS["Physical Layer<br/><i>Serial/Ethernet</i>"]
    end

    APP --> TRANS
    TRANS --> LINK
    LINK --> PHYS
```

**Key Features:**

- Event-based reporting (unsolicited responses)
- Time synchronization
- Secure authentication (SA v5)
- Object-oriented data model

### OPC-UA (Open Platform Communications Unified Architecture)

Modern, IT-friendly protocol for industrial interoperability.

**Characteristics:**

- Platform independent
- Built-in security (encryption, authentication)
- Complex data types
- Pub/Sub and client-server models
- Information modeling

## Traffic Characteristics

ICS traffic is fundamentally different from IT traffic:

| Characteristic | IT Traffic        | ICS Traffic         |
| -------------- | ----------------- | ------------------- |
| Volume         | High, variable    | Low, predictable    |
| Patterns       | Irregular         | Highly periodic     |
| Endpoints      | Dynamic           | Static, known       |
| Protocols      | HTTP, SQL, etc.   | Modbus, DNP3, OPC   |
| Tolerance      | Retries OK        | Real-time critical  |
| Lifespan       | Short connections | Long-lived sessions |

### Traffic Patterns

```mermaid
xychart-beta
    title "Typical ICS Traffic Pattern (1 hour)"
    x-axis ["0", "10", "20", "30", "40", "50", "60"]
    y-axis "Packets/sec" 0 --> 100
    line [50, 52, 48, 51, 50, 49, 51, 50, 52, 48, 51, 50, 49]
```

**Normal characteristics:**

- Consistent polling intervals (100ms - 10s typical)
- Predictable packet sizes
- Fixed communication pairs
- Low variation in function codes

## Why This Matters for Anomaly Detection

The deterministic nature of ICS traffic creates both opportunities and challenges:

**Opportunities:**

- Easy to establish baselines
- Small deviations are significant
- Fewer false positives from "normal noise"

**Challenges:**

- Legitimate changes (maintenance) look anomalous
- Low traffic volume means fewer samples
- Protocol diversity requires multiple parsers
- Safety requirements prohibit active responses
