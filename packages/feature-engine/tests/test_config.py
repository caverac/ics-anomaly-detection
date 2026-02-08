"""Tests for configuration."""



from src.config import KafkaSettings, Settings, WindowSettings, get_settings


class TestKafkaSettings:
    """Tests for KafkaSettings."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = KafkaSettings()

        assert settings.bootstrap_servers == "localhost:9092"
        assert settings.group_id == "feature-engine"
        assert settings.client_id == "feature-engine-client"
        assert settings.auto_offset_reset == "earliest"
        assert "ics.parsed.modbus" in settings.input_topics
        assert settings.output_topic == "ics.features"

    def test_env_override(self, monkeypatch):
        """Test environment variable overrides."""
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        monkeypatch.setenv("KAFKA_GROUP_ID", "test-group")
        monkeypatch.setenv("KAFKA_OUTPUT_TOPIC", "test.features")

        settings = KafkaSettings()

        assert settings.bootstrap_servers == "kafka:29092"
        assert settings.group_id == "test-group"
        assert settings.output_topic == "test.features"


class TestWindowSettings:
    """Tests for WindowSettings."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = WindowSettings()

        assert settings.window_sizes == [60, 300, 900]
        assert settings.emit_interval == 60
        assert settings.max_buffer_size == 100000

    def test_env_override(self, monkeypatch):
        """Test environment variable overrides."""
        monkeypatch.setenv("WINDOW_EMIT_INTERVAL", "30")
        monkeypatch.setenv("WINDOW_MAX_BUFFER_SIZE", "50000")

        settings = WindowSettings()

        assert settings.emit_interval == 30
        assert settings.max_buffer_size == 50000


class TestSettings:
    """Tests for main Settings."""

    def test_nested_settings(self):
        """Test that nested settings are created correctly."""
        settings = Settings()

        assert settings.kafka is not None
        assert settings.windows is not None
        assert isinstance(settings.kafka, KafkaSettings)
        assert isinstance(settings.windows, WindowSettings)

    def test_default_log_level(self):
        """Test default log level."""
        settings = Settings()

        assert settings.log_level == "INFO"
        assert settings.log_format == "json"

    def test_get_settings(self):
        """Test get_settings helper."""
        settings = get_settings()

        assert isinstance(settings, Settings)
