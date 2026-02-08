---
sidebar_position: 2
---

# Attack Scenarios

Pre-built attack scenarios for testing the detection engine.

## Available Attack Modes

The simulator supports four attack modes that can be triggered via API:

```mermaid
flowchart TB
    subgraph Modes["Attack Modes"]
        A1["reconnaissance<br/><i>Device scanning</i>"]
        A2["write_attack<br/><i>Unauthorized writes</i>"]
        A3["replay<br/><i>Traffic replay</i>"]
        A4["dos<br/><i>Flood attack</i>"]
    end

    style A1 fill:#457b9d,color:#fff
    style A2 fill:#e63946,color:#fff
    style A3 fill:#f4a261,color:#000
    style A4 fill:#e63946,color:#fff
```

## Scenario: Reconnaissance

Simulates device enumeration using Read Device Identification (FC 0x2B).

### Attack Pattern

```mermaid
sequenceDiagram
    participant ATK as Attacker (HMI)
    participant PLC1 as PLC 1
    participant PLC2 as PLC 2
    participant PLC3 as PLC 3

    loop Scanning
        ATK->>PLC1: Read Device ID (FC 0x2B)
        PLC1-->>ATK: Device Info
        ATK->>PLC2: Read Device ID (FC 0x2B)
        PLC2-->>ATK: Device Info
        ATK->>PLC3: Read Device ID (FC 0x2B)
        PLC3-->>ATK: Device Info
    end
```

### Trigger

```bash
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "reconnaissance"}'
```

### Expected Detection

| Feature | Normal | During Attack |
|---------|--------|---------------|
| `fc_unique_count` | 2-4 | 5+ (includes 0x2B) |
| `fc_diagnostic_ratio` | < 0.1 | > 0.5 |

**Expected Alert:** `RECONNAISSANCE` severity `HIGH`

---

## Scenario: Write Attack

Simulates unauthorized write operations targeting PLC registers.

### Attack Pattern

```mermaid
sequenceDiagram
    participant ATK as Attacker
    participant PLC as Target PLC
    participant PROC as Physical Process

    Note over ATK,PROC: Attacker sends malicious writes

    ATK->>PLC: Write Single Register (FC 0x06)
    PLC-->>ATK: Write confirmed
    ATK->>PLC: Write Multiple Registers (FC 0x10)
    PLC-->>ATK: Write confirmed
    ATK->>PLC: Write Single Coil (FC 0x05)
    PLC-->>ATK: Write confirmed
```

### Trigger

```bash
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "write_attack"}'
```

### Expected Detection

| Feature | Normal | During Attack |
|---------|--------|---------------|
| `fc_write_ratio` | < 0.2 | > 0.5 |
| `fc_read_ratio` | > 0.8 | < 0.5 |

**Expected Alert:** `COMMAND_INJECTION` severity `CRITICAL`

---

## Scenario: Replay Attack

:::note Planned Feature
Replay attack simulation (replaying captured traffic) is defined but not fully implemented. Currently behaves the same as normal traffic.
:::

### Trigger

```bash
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "replay"}'
```

---

## Scenario: DoS Flood

:::note Planned Feature
DoS flood simulation is defined but not fully implemented. Currently behaves the same as normal traffic.
:::

### Trigger

```bash
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "dos"}'
```

### Expected Detection (when implemented)

| Feature | Normal | During Attack |
|---------|--------|---------------|
| `message_count` | 100/min | 60000+/min |
| `iat_mean` | 600ms | < 1ms |

**Expected Alert:** `VOLUME_ANOMALY` severity `CRITICAL`

---

## Running Attacks

### Via API

```bash
# Start an attack
curl -X POST http://localhost:8083/attack/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "reconnaissance"}'

# Check current status
curl http://localhost:8083/status

# Stop attack (returns to normal traffic)
curl -X POST http://localhost:8083/attack/stop
```

### Via Make Targets

```bash
# Start reconnaissance attack
make attack-recon

# Stop any running attack
make attack-stop
```

## Monitoring Attack Effects

### Watch Feature Changes

```bash
# Consume features topic to see impact
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ics.features \
  --from-latest
```

### Watch Anomaly Scores

```bash
# Consume anomalies topic
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ics.anomalies \
  --from-latest
```

### View in Dashboard

Open http://localhost:5173 to see:
- Real-time anomaly score changes
- Alert generation
- Feature deviations

## Creating Custom Scenarios

The current simulator uses hardcoded attack modes. To add new scenarios:

1. Add mode to `AttackConfig` validation in `main.py`
2. Implement logic in `ModbusGenerator.generate_message()`
3. Handle the mode in the generator switch statement

Example extension point in `packages/simulator/src/main.py`:

```python
def generate_message(self, attack_mode: Optional[str] = None) -> dict:
    if attack_mode == "reconnaissance":
        function_code = 0x2B  # Read Device Identification
    elif attack_mode == "write_attack":
        function_code = random.choice([0x06, 0x10, 0x05])
    elif attack_mode == "my_custom_attack":
        # Add your custom logic here
        function_code = 0x08  # Diagnostics
    else:
        # Normal weighted selection
        ...
```
