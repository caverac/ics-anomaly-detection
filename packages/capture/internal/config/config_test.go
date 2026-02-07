package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	// Test Capture defaults
	if cfg.Capture.Interface != "eth0" {
		t.Errorf("Capture.Interface = %s, want eth0", cfg.Capture.Interface)
	}
	if cfg.Capture.SnapLen != 1600 {
		t.Errorf("Capture.SnapLen = %d, want 1600", cfg.Capture.SnapLen)
	}
	if !cfg.Capture.Promiscuous {
		t.Error("Capture.Promiscuous = false, want true")
	}
	if cfg.Capture.TimeoutMs != 100 {
		t.Errorf("Capture.TimeoutMs = %d, want 100", cfg.Capture.TimeoutMs)
	}
	if cfg.Capture.BufferSize != 64 {
		t.Errorf("Capture.BufferSize = %d, want 64", cfg.Capture.BufferSize)
	}

	// Test Kafka defaults
	if len(cfg.Kafka.Brokers) != 1 || cfg.Kafka.Brokers[0] != "localhost:9092" {
		t.Errorf("Kafka.Brokers = %v, want [localhost:9092]", cfg.Kafka.Brokers)
	}
	if cfg.Kafka.Topic != "ics.raw.packets" {
		t.Errorf("Kafka.Topic = %s, want ics.raw.packets", cfg.Kafka.Topic)
	}
	if cfg.Kafka.BatchSize != 100 {
		t.Errorf("Kafka.BatchSize = %d, want 100", cfg.Kafka.BatchSize)
	}
	if cfg.Kafka.BatchTimeoutMs != 100 {
		t.Errorf("Kafka.BatchTimeoutMs = %d, want 100", cfg.Kafka.BatchTimeoutMs)
	}
	if cfg.Kafka.CompressionType != "gzip" {
		t.Errorf("Kafka.CompressionType = %s, want gzip", cfg.Kafka.CompressionType)
	}

	// Test Logging defaults
	if cfg.Logging.Level != "info" {
		t.Errorf("Logging.Level = %s, want info", cfg.Logging.Level)
	}
	if cfg.Logging.Format != "json" {
		t.Errorf("Logging.Format = %s, want json", cfg.Logging.Format)
	}
}

func TestLoadWithoutConfigFile(t *testing.T) {
	// Clear any environment variables that might interfere
	envVars := []string{
		"CAPTURE_INTERFACE",
		"KAFKA_BROKERS",
		"LOGGING_LEVEL",
	}
	for _, env := range envVars {
		_ = os.Unsetenv(env)
	}

	cfg, err := Load("")
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	// Should return default config
	if cfg.Capture.Interface != "eth0" {
		t.Errorf("Capture.Interface = %s, want eth0", cfg.Capture.Interface)
	}
}

func TestLoadWithEnvOverrides(t *testing.T) {
	// Set environment variables
	t.Setenv("CAPTURE_INTERFACE", "lo0")
	t.Setenv("KAFKA_TOPIC", "test.topic")
	t.Setenv("LOGGING_LEVEL", "debug")

	cfg, err := Load("")
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	if cfg.Capture.Interface != "lo0" {
		t.Errorf("Capture.Interface = %s, want lo0", cfg.Capture.Interface)
	}
	if cfg.Kafka.Topic != "test.topic" {
		t.Errorf("Kafka.Topic = %s, want test.topic", cfg.Kafka.Topic)
	}
	if cfg.Logging.Level != "debug" {
		t.Errorf("Logging.Level = %s, want debug", cfg.Logging.Level)
	}
}

func TestLoadWithConfigFile(t *testing.T) {
	// Create a temporary config file
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.yaml")

	configContent := `
capture:
  interface: "en0"
  snap_len: 2000
  promiscuous: false
  timeout_ms: 200
  bpf_filter: "tcp port 502"
  buffer_size: 128

kafka:
  brokers:
    - "kafka1:9092"
    - "kafka2:9092"
  topic: "custom.topic"
  batch_size: 200
  batch_timeout_ms: 50
  compression_type: "snappy"

logging:
  level: "warn"
  format: "console"
`
	if err := os.WriteFile(configPath, []byte(configContent), 0o600); err != nil {
		t.Fatalf("Failed to write config file: %v", err)
	}

	cfg, err := Load(configPath)
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	// Verify config file values
	if cfg.Capture.Interface != "en0" {
		t.Errorf("Capture.Interface = %s, want en0", cfg.Capture.Interface)
	}
	if cfg.Capture.SnapLen != 2000 {
		t.Errorf("Capture.SnapLen = %d, want 2000", cfg.Capture.SnapLen)
	}
	if cfg.Capture.Promiscuous {
		t.Error("Capture.Promiscuous = true, want false")
	}
	if cfg.Capture.TimeoutMs != 200 {
		t.Errorf("Capture.TimeoutMs = %d, want 200", cfg.Capture.TimeoutMs)
	}
	if cfg.Capture.BufferSize != 128 {
		t.Errorf("Capture.BufferSize = %d, want 128", cfg.Capture.BufferSize)
	}

	if len(cfg.Kafka.Brokers) != 2 {
		t.Errorf("len(Kafka.Brokers) = %d, want 2", len(cfg.Kafka.Brokers))
	}
	if cfg.Kafka.Topic != "custom.topic" {
		t.Errorf("Kafka.Topic = %s, want custom.topic", cfg.Kafka.Topic)
	}
	if cfg.Kafka.CompressionType != "snappy" {
		t.Errorf("Kafka.CompressionType = %s, want snappy", cfg.Kafka.CompressionType)
	}

	if cfg.Logging.Level != "warn" {
		t.Errorf("Logging.Level = %s, want warn", cfg.Logging.Level)
	}
	if cfg.Logging.Format != "console" {
		t.Errorf("Logging.Format = %s, want console", cfg.Logging.Format)
	}
}

func TestLoadWithInvalidConfigFile(t *testing.T) {
	_, err := Load("/nonexistent/path/config.yaml")
	if err == nil {
		t.Error("Load() expected error for nonexistent file, got nil")
	}
}

func TestLoadWithMalformedConfigFile(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.yaml")

	// Write invalid YAML
	if err := os.WriteFile(configPath, []byte("invalid: yaml: content: ["), 0o600); err != nil {
		t.Fatalf("Failed to write config file: %v", err)
	}

	_, err := Load(configPath)
	if err == nil {
		t.Error("Load() expected error for malformed YAML, got nil")
	}
}

func TestCaptureConfigBPFFilter(t *testing.T) {
	cfg := DefaultConfig()

	expectedFilter := "tcp port 502 or tcp port 20000 or tcp port 4840 or tcp port 44818"
	if cfg.Capture.BPFFilter != expectedFilter {
		t.Errorf("Capture.BPFFilter = %s, want %s", cfg.Capture.BPFFilter, expectedFilter)
	}
}
