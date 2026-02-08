#!/usr/bin/env python3
"""
ICS Traffic Simulator

Generates synthetic Modbus/DNP3 traffic and publishes to Kafka
for testing the anomaly detection pipeline.
"""

import asyncio
import json
import logging
import random
import struct
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import uvicorn
from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings
from starlette.responses import Response

# =============================================================================
# Configuration
# =============================================================================


class Settings(BaseSettings):
    kafka_brokers: str = "localhost:9092"
    kafka_topic: str = "ics.raw.packets"
    simulator_rate: int = 100  # messages per second
    simulator_protocol: str = "modbus"  # modbus, dnp3, mixed
    metrics_port: int = 8083

    model_config = ConfigDict(env_prefix="")


settings = Settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# =============================================================================
# Metrics
# =============================================================================

MESSAGES_SENT = Counter("simulator_messages_sent_total", "Total messages sent", ["protocol"])
MESSAGES_ERRORS = Counter("simulator_errors_total", "Total errors")
MESSAGE_LATENCY = Histogram("simulator_message_latency_seconds", "Message generation latency")

# =============================================================================
# Simulated Devices
# =============================================================================

MODBUS_DEVICES = [
    {"ip": "192.168.1.10", "unit_id": 1, "type": "plc", "registers": range(0, 100)},
    {"ip": "192.168.1.11", "unit_id": 2, "type": "plc", "registers": range(100, 200)},
    {"ip": "192.168.1.12", "unit_id": 3, "type": "plc", "registers": range(200, 300)},
    {"ip": "192.168.1.20", "unit_id": 1, "type": "rtu", "registers": range(0, 50)},
]

HMI_DEVICES = [
    {"ip": "192.168.1.100", "type": "hmi"},
    {"ip": "192.168.1.101", "type": "hmi"},
]

# =============================================================================
# Modbus Traffic Generator
# =============================================================================


class ModbusGenerator:
    """Generate realistic Modbus TCP traffic."""

    FUNCTION_CODES = {
        0x03: ("Read Holding Registers", 0.6),  # Most common
        0x04: ("Read Input Registers", 0.2),
        0x06: ("Write Single Register", 0.1),
        0x10: ("Write Multiple Registers", 0.05),
        0x01: ("Read Coils", 0.03),
        0x05: ("Write Single Coil", 0.02),
    }

    def __init__(self):
        self.transaction_id = 0
        self.register_values = {}  # Simulated register state

    def generate_message(self, attack_mode: str | None = None) -> dict:
        """Generate a Modbus TCP message."""
        self.transaction_id = (self.transaction_id + 1) % 65536

        # Select source (HMI) and destination (PLC)
        hmi = random.choice(HMI_DEVICES)
        plc = random.choice(MODBUS_DEVICES)

        # Select function code based on weights (or attack mode)
        if attack_mode == "reconnaissance":
            function_code = 0x2B  # Read Device Identification
        elif attack_mode == "write_attack":
            function_code = random.choice([0x06, 0x10, 0x05])
        else:
            function_code = random.choices(
                list(self.FUNCTION_CODES.keys()),
                weights=[fc[1] for fc in self.FUNCTION_CODES.values()],
            )[0]

        # Generate PDU based on function code
        payload = self._generate_pdu(function_code, plc)

        # Build MBAP header
        length = len(payload) + 1  # +1 for unit_id
        mbap = struct.pack(">HHHB", self.transaction_id, 0, length, plc["unit_id"])
        full_payload = mbap + payload

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "src_ip": hmi["ip"],
            "dst_ip": plc["ip"],
            "src_port": random.randint(49152, 65535),
            "dst_port": 502,
            "protocol": "tcp",
            "ics_protocol": "modbus",
            "payload_size": len(full_payload),
            "payload_hex": full_payload.hex(),
        }

    def _generate_pdu(self, function_code: int, plc: dict) -> bytes:
        """Generate Modbus PDU for a function code."""
        registers = list(plc["registers"])
        max_addr = len(registers) - 1

        if function_code in (0x03, 0x04):  # Read Holding/Input Registers
            address = random.randint(0, max(0, max_addr - 10))
            quantity = random.randint(1, 10)
            return struct.pack(">BHH", function_code, address, quantity)

        elif function_code == 0x06:  # Write Single Register
            address = random.choice(registers)
            value = random.randint(0, 65535)
            return struct.pack(">BHH", function_code, address, value)

        elif function_code == 0x10:  # Write Multiple Registers
            address = random.randint(0, max(0, max_addr - 10))
            quantity = random.randint(2, 5)
            values = [random.randint(0, 65535) for _ in range(quantity)]
            byte_count = quantity * 2
            return struct.pack(
                f">BHH B{'H' * quantity}",
                function_code, address, quantity, byte_count, *values
            )

        elif function_code == 0x01:  # Read Coils
            address = random.randint(0, 100)
            quantity = random.randint(1, 16)
            return struct.pack(">BHH", function_code, address, quantity)

        elif function_code == 0x05:  # Write Single Coil
            address = random.randint(0, 100)
            value = random.choice([0x0000, 0xFF00])
            return struct.pack(">BHH", function_code, address, value)

        elif function_code == 0x2B:  # Read Device Identification
            return struct.pack(">BBB", function_code, 0x0E, 0x01)

        else:
            return struct.pack(">B", function_code)


# =============================================================================
# Simulator Engine
# =============================================================================


class Simulator:
    def __init__(self):
        self.producer: Producer | None = None
        self.running = False
        self.rate = settings.simulator_rate
        self.protocol = settings.simulator_protocol
        self.attack_mode: str | None = None
        self.modbus_gen = ModbusGenerator()

    def connect(self):
        """Connect to Kafka."""
        try:
            self.producer = Producer({
                "bootstrap.servers": settings.kafka_brokers,
                "compression.type": "gzip",
                "batch.size": 16384,
                "linger.ms": 5,
            })
            logger.info(f"Connected to Kafka: {settings.kafka_brokers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    def _delivery_callback(self, err, msg):
        """Handle delivery reports."""
        if err:
            MESSAGES_ERRORS.inc()
            logger.error(f"Message delivery failed: {err}")

    def generate_message(self) -> dict:
        """Generate a message based on current protocol."""
        if self.protocol == "modbus":
            return self.modbus_gen.generate_message(self.attack_mode)
        elif self.protocol == "mixed":
            # 80% Modbus, 20% placeholder for others
            if random.random() < 0.8:
                return self.modbus_gen.generate_message(self.attack_mode)
            else:
                return self.modbus_gen.generate_message(self.attack_mode)
        else:
            return self.modbus_gen.generate_message(self.attack_mode)

    async def run(self):
        """Main simulation loop."""
        self.running = True
        interval = 1.0 / self.rate
        msg_count = 0

        logger.info(f"Starting simulator: rate={self.rate}/s, protocol={self.protocol}")

        while self.running:
            try:
                with MESSAGE_LATENCY.time():
                    msg = self.generate_message()
                    key = f"{msg['src_ip']}:{msg['dst_ip']}"
                    self.producer.produce(
                        topic=settings.kafka_topic,
                        key=key.encode("utf-8"),
                        value=json.dumps(msg).encode("utf-8"),
                        callback=self._delivery_callback,
                    )
                    msg_count += 1
                    MESSAGES_SENT.labels(protocol=msg["ics_protocol"]).inc()

                    # Flush every 100 messages
                    if msg_count % 100 == 0:
                        self.producer.flush(timeout=1)
                    else:
                        self.producer.poll(0)  # Trigger callbacks

                await asyncio.sleep(interval)

            except Exception as e:
                MESSAGES_ERRORS.inc()
                logger.error(f"Error generating message: {e}")
                await asyncio.sleep(1)

    def stop(self):
        """Stop the simulator."""
        self.running = False
        if self.producer:
            self.producer.flush(timeout=5)


# =============================================================================
# API
# =============================================================================

simulator = Simulator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    simulator.connect()
    asyncio.create_task(simulator.run())
    yield
    simulator.stop()


app = FastAPI(title="ICS Traffic Simulator", lifespan=lifespan)


@app.get("/")
async def root():
    """List all available API endpoints."""
    return {
        "service": "ICS Traffic Simulator",
        "version": "0.1.0",
        "endpoints": {
            "GET /": "This endpoint - list available endpoints",
            "GET /health": "Health check",
            "GET /metrics": "Prometheus metrics",
            "GET /status": "Current simulator status",
            "POST /config": "Update simulator config (rate, protocol)",
            "POST /attack/start": "Start attack simulation (mode: reconnaissance, write_attack, replay, dos)",
            "POST /attack/stop": "Stop attack simulation",
        },
        "docs": "/docs",
    }


class TrafficConfig(BaseModel):
    rate: int | None = None
    protocol: str | None = None


class AttackConfig(BaseModel):
    mode: str  # reconnaissance, write_attack, replay, dos


@app.get("/health")
async def health():
    return {"status": "healthy", "running": simulator.running}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/status")
async def status():
    return {
        "running": simulator.running,
        "rate": simulator.rate,
        "protocol": simulator.protocol,
        "attack_mode": simulator.attack_mode,
    }


@app.post("/config")
async def configure(config: TrafficConfig):
    if config.rate:
        simulator.rate = config.rate
    if config.protocol:
        simulator.protocol = config.protocol
    return {"status": "updated", "rate": simulator.rate, "protocol": simulator.protocol}


@app.post("/attack/start")
async def start_attack(config: AttackConfig):
    if config.mode not in ["reconnaissance", "write_attack", "replay", "dos"]:
        raise HTTPException(status_code=400, detail="Invalid attack mode")
    simulator.attack_mode = config.mode
    return {"status": "attack_started", "mode": config.mode}


@app.post("/attack/stop")
async def stop_attack():
    simulator.attack_mode = None
    return {"status": "attack_stopped"}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.metrics_port)
