"""Tests for feature vector."""


import pytest

from src.features.vector import FeatureVector, WindowMetadata


class TestWindowMetadata:
    """Tests for WindowMetadata."""

    def test_metadata_creation(self):
        """Test creating window metadata."""
        metadata = WindowMetadata(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="modbus",
            window_size=60,
            window_start=1000,
        )

        assert metadata.src_ip == "192.168.1.1"
        assert metadata.dst_ip == "192.168.1.2"
        assert metadata.protocol == "modbus"
        assert metadata.window_size == 60
        assert metadata.window_start == 1000


class TestFeatureVector:
    """Tests for FeatureVector."""

    @pytest.fixture
    def sample_features(self):
        """Create sample features dictionary."""
        return {
            "_window_key": {
                "src_ip": "192.168.1.1",
                "dst_ip": "192.168.1.2",
                "protocol": "modbus",
                "window_size": 60,
                "window_start": 1000,
            },
            "_extracted_at": "2024-01-01T12:00:00+00:00",
            "protocol": "modbus",
            "window_size_seconds": 60,
            "message_count": 100,
            "bytes_total": 5000,
            "bytes_mean": 50.0,
            "bytes_std": 10.0,
            "bytes_min": 20,
            "bytes_max": 100,
            "iat_mean": 0.5,
            "iat_std": 0.1,
            "iat_min": 0.1,
            "iat_max": 1.0,
            "iat_median": 0.5,
            "fc_unique_count": 3,
            "fc_read_ratio": 0.7,
            "fc_write_ratio": 0.3,
        }

    def test_from_features(self, sample_features):
        """Test creating a feature vector from dictionary."""
        vector = FeatureVector.from_features(sample_features)

        assert vector.protocol == "modbus"
        assert vector.message_count == 100
        assert vector.bytes_total == 5000
        assert vector.window_key.src_ip == "192.168.1.1"

    def test_to_ml_input(self, sample_features):
        """Test converting to ML input format."""
        vector = FeatureVector.from_features(sample_features)
        ml_input = vector.to_ml_input()

        # Should include numeric features
        assert "message_count" in ml_input
        assert "bytes_total" in ml_input
        assert "iat_mean" in ml_input
        assert "fc_read_ratio" in ml_input

        # Should exclude metadata and string fields
        assert "protocol" not in ml_input
        assert "_window_key" not in ml_input
        assert "_extracted_at" not in ml_input
        assert "window_key" not in ml_input
        assert "extracted_at" not in ml_input

    def test_get_feature_names(self, sample_features):
        """Test getting feature names."""
        vector = FeatureVector.from_features(sample_features)
        names = vector.get_feature_names()

        assert isinstance(names, list)
        assert len(names) > 0
        assert names == sorted(names)  # Should be sorted
        assert "message_count" in names

    def test_extra_fields_allowed(self, sample_features):
        """Test that extra protocol-specific fields are preserved."""
        sample_features["custom_feature"] = 42.0
        vector = FeatureVector.from_features(sample_features)

        # Extra fields should be accessible via model_dump
        data = vector.model_dump()
        assert data.get("custom_feature") == 42.0

    def test_default_values(self):
        """Test default values for missing features."""
        minimal_features = {
            "_window_key": {
                "src_ip": "192.168.1.1",
                "dst_ip": "192.168.1.2",
                "protocol": "modbus",
                "window_size": 60,
                "window_start": 1000,
            },
            "_extracted_at": "2024-01-01T12:00:00+00:00",
            "protocol": "modbus",
            "window_size_seconds": 60,
        }
        vector = FeatureVector.from_features(minimal_features)

        assert vector.message_count == 0
        assert vector.bytes_total == 0
        assert vector.iat_mean == 0.0

    def test_json_serialization(self, sample_features):
        """Test JSON serialization for Kafka."""
        vector = FeatureVector.from_features(sample_features)
        json_data = vector.model_dump(mode="json", by_alias=True)

        assert isinstance(json_data, dict)
        assert json_data["protocol"] == "modbus"
        # Datetime should be serialized as string with alias
        assert isinstance(json_data["_extracted_at"], str)

    def test_model_dump_by_alias(self, sample_features):
        """Test model dump with aliases."""
        vector = FeatureVector.from_features(sample_features)

        # With aliases (default for Kafka output)
        with_alias = vector.model_dump(by_alias=True)
        assert "_window_key" in with_alias
        assert "_extracted_at" in with_alias

        # Without aliases
        without_alias = vector.model_dump(by_alias=False)
        assert "window_key" in without_alias
        assert "extracted_at" in without_alias
