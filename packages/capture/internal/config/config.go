// Package config provides configuration loading for the ICS capture service.
package config

import (
	"fmt"
	"strings"

	"github.com/spf13/viper"
)

// Config holds all configuration for the capture service
type Config struct {
	Capture CaptureConfig `mapstructure:"capture"`
	Kafka   KafkaConfig   `mapstructure:"kafka"`
	Logging LoggingConfig `mapstructure:"logging"`
}

// CaptureConfig holds packet capture settings
type CaptureConfig struct {
	Interface   string `mapstructure:"interface"`
	SnapLen     int32  `mapstructure:"snap_len"`
	Promiscuous bool   `mapstructure:"promiscuous"`
	TimeoutMs   int    `mapstructure:"timeout_ms"`
	BPFFilter   string `mapstructure:"bpf_filter"`
	BufferSize  int    `mapstructure:"buffer_size"` // Ring buffer size in MB
}

// KafkaConfig holds Kafka producer settings
type KafkaConfig struct {
	Brokers         []string `mapstructure:"brokers"`
	Topic           string   `mapstructure:"topic"`
	BatchSize       int      `mapstructure:"batch_size"`
	BatchTimeoutMs  int      `mapstructure:"batch_timeout_ms"`
	CompressionType string   `mapstructure:"compression_type"`
}

// LoggingConfig holds logging settings
type LoggingConfig struct {
	Level  string `mapstructure:"level"`
	Format string `mapstructure:"format"` // "json" or "console"
}

// DefaultConfig returns configuration with sensible defaults
func DefaultConfig() *Config {
	return &Config{
		Capture: CaptureConfig{
			Interface:   "eth0",
			SnapLen:     1600,
			Promiscuous: true,
			TimeoutMs:   100,
			BPFFilter:   "tcp port 502 or tcp port 20000 or tcp port 4840 or tcp port 44818",
			BufferSize:  64, // 64MB
		},
		Kafka: KafkaConfig{
			Brokers:         []string{"localhost:9092"},
			Topic:           "ics.raw.packets",
			BatchSize:       100,
			BatchTimeoutMs:  100,
			CompressionType: "gzip",
		},
		Logging: LoggingConfig{
			Level:  "info",
			Format: "json",
		},
	}
}

// Load reads configuration from file and environment
func Load(configPath string) (*Config, error) {
	cfg := DefaultConfig()

	v := viper.New()
	v.SetConfigType("yaml")

	// Set defaults
	v.SetDefault("capture.interface", cfg.Capture.Interface)
	v.SetDefault("capture.snap_len", cfg.Capture.SnapLen)
	v.SetDefault("capture.promiscuous", cfg.Capture.Promiscuous)
	v.SetDefault("capture.timeout_ms", cfg.Capture.TimeoutMs)
	v.SetDefault("capture.bpf_filter", cfg.Capture.BPFFilter)
	v.SetDefault("capture.buffer_size", cfg.Capture.BufferSize)
	v.SetDefault("kafka.brokers", cfg.Kafka.Brokers)
	v.SetDefault("kafka.topic", cfg.Kafka.Topic)
	v.SetDefault("kafka.batch_size", cfg.Kafka.BatchSize)
	v.SetDefault("kafka.batch_timeout_ms", cfg.Kafka.BatchTimeoutMs)
	v.SetDefault("kafka.compression_type", cfg.Kafka.CompressionType)
	v.SetDefault("logging.level", cfg.Logging.Level)
	v.SetDefault("logging.format", cfg.Logging.Format)

	// Environment variables (CAPTURE_INTERFACE, KAFKA_BROKERS, etc.)
	v.SetEnvPrefix("")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	// Read config file if provided
	if configPath != "" {
		v.SetConfigFile(configPath)
		if err := v.ReadInConfig(); err != nil {
			return nil, fmt.Errorf("failed to read config file: %w", err)
		}
	}

	if err := v.Unmarshal(cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	return cfg, nil
}
