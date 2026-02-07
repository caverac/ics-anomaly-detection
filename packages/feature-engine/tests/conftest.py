"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_parsed_message():
    """Create a sample parsed message from the parser."""
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "src_ip": "192.168.1.1",
        "dst_ip": "192.168.1.2",
        "src_port": 50000,
        "dst_port": 502,
        "protocol": "modbus",
        "payload_size": 100,
        "message": {
            "function_code": 3,
            "unit_id": 1,
            "start_address": 0,
            "quantity": 10,
        },
    }


@pytest.fixture
def sample_kafka_settings():
    """Create sample Kafka settings for testing."""
    return {
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "KAFKA_INPUT_TOPIC": "test-parsed",
        "KAFKA_OUTPUT_TOPIC": "test-features",
        "KAFKA_CONSUMER_GROUP": "test-group",
    }
