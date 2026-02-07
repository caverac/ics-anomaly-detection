package kafka

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/caverac/ics-anomaly-detection/packages/capture/internal/config"
	"github.com/caverac/ics-anomaly-detection/packages/capture/pkg/types"
	"go.uber.org/zap"
)

func TestNewProducerWithGzipCompression(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers:         []string{"localhost:9092"},
		Topic:           "test.topic",
		BatchSize:       100,
		BatchTimeoutMs:  100,
		CompressionType: "gzip",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}
	defer func() { _ = producer.Close() }()

	if producer == nil {
		t.Fatal("NewProducer() returned nil")
	}
	if producer.config.Topic != "test.topic" {
		t.Errorf("config.Topic = %s, want test.topic", producer.config.Topic)
	}
}

func TestNewProducerWithSnappyCompression(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers:         []string{"localhost:9092"},
		Topic:           "test.topic",
		CompressionType: "snappy",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}
	defer func() { _ = producer.Close() }()

	if producer == nil {
		t.Fatal("NewProducer() returned nil")
	}
}

func TestNewProducerWithLz4Compression(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers:         []string{"localhost:9092"},
		Topic:           "test.topic",
		CompressionType: "lz4",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}
	defer func() { _ = producer.Close() }()

	if producer == nil {
		t.Fatal("NewProducer() returned nil")
	}
}

func TestNewProducerWithZstdCompression(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers:         []string{"localhost:9092"},
		Topic:           "test.topic",
		CompressionType: "zstd",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}
	defer func() { _ = producer.Close() }()

	if producer == nil {
		t.Fatal("NewProducer() returned nil")
	}
}

func TestNewProducerWithNoCompression(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers:         []string{"localhost:9092"},
		Topic:           "test.topic",
		CompressionType: "none",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}
	defer func() { _ = producer.Close() }()

	if producer == nil {
		t.Fatal("NewProducer() returned nil")
	}
}

func TestNewProducerWithMultipleBrokers(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers:         []string{"broker1:9092", "broker2:9092", "broker3:9092"},
		Topic:           "test.topic",
		CompressionType: "gzip",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}
	defer func() { _ = producer.Close() }()

	if len(producer.config.Brokers) != 3 {
		t.Errorf("len(config.Brokers) = %d, want 3", len(producer.config.Brokers))
	}
}

func TestProducerClose(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers: []string{"localhost:9092"},
		Topic:   "test.topic",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}

	// Close should not return error
	err = producer.Close()
	if err != nil {
		t.Errorf("Close() error = %v", err)
	}
}

func TestProducerCloseNilWriter(t *testing.T) {
	producer := &Producer{
		logger: zap.NewNop(),
		writer: nil,
	}

	// Close with nil writer should not panic or error
	err := producer.Close()
	if err != nil {
		t.Errorf("Close() with nil writer error = %v", err)
	}
}

func TestPacketMessageSerialization(t *testing.T) {
	msg := PacketMessage{
		Timestamp:   "2024-01-15T10:30:00.123456789Z",
		SrcIP:       "192.168.1.1",
		DstIP:       "192.168.1.2",
		SrcPort:     49152,
		DstPort:     502,
		Protocol:    "tcp",
		ICSProtocol: "modbus",
		PayloadSize: 12,
		PayloadHex:  "00010000000601030000000a",
	}

	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("json.Marshal() error = %v", err)
	}

	var decoded PacketMessage
	err = json.Unmarshal(data, &decoded)
	if err != nil {
		t.Fatalf("json.Unmarshal() error = %v", err)
	}

	if decoded.SrcIP != msg.SrcIP {
		t.Errorf("decoded.SrcIP = %s, want %s", decoded.SrcIP, msg.SrcIP)
	}
	if decoded.DstIP != msg.DstIP {
		t.Errorf("decoded.DstIP = %s, want %s", decoded.DstIP, msg.DstIP)
	}
	if decoded.SrcPort != msg.SrcPort {
		t.Errorf("decoded.SrcPort = %d, want %d", decoded.SrcPort, msg.SrcPort)
	}
	if decoded.DstPort != msg.DstPort {
		t.Errorf("decoded.DstPort = %d, want %d", decoded.DstPort, msg.DstPort)
	}
	if decoded.Protocol != msg.Protocol {
		t.Errorf("decoded.Protocol = %s, want %s", decoded.Protocol, msg.Protocol)
	}
	if decoded.ICSProtocol != msg.ICSProtocol {
		t.Errorf("decoded.ICSProtocol = %s, want %s", decoded.ICSProtocol, msg.ICSProtocol)
	}
	if decoded.PayloadSize != msg.PayloadSize {
		t.Errorf("decoded.PayloadSize = %d, want %d", decoded.PayloadSize, msg.PayloadSize)
	}
	if decoded.PayloadHex != msg.PayloadHex {
		t.Errorf("decoded.PayloadHex = %s, want %s", decoded.PayloadHex, msg.PayloadHex)
	}
}

func TestPacketMessageJSONStructure(t *testing.T) {
	msg := PacketMessage{
		Timestamp:   "2024-01-15T10:30:00Z",
		SrcIP:       "10.0.0.1",
		DstIP:       "10.0.0.2",
		SrcPort:     12345,
		DstPort:     502,
		Protocol:    "tcp",
		ICSProtocol: "modbus",
		PayloadSize: 0,
		PayloadHex:  "",
	}

	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("json.Marshal() error = %v", err)
	}

	// Verify JSON field names
	var raw map[string]interface{}
	err = json.Unmarshal(data, &raw)
	if err != nil {
		t.Fatalf("json.Unmarshal() error = %v", err)
	}

	expectedFields := []string{
		"timestamp", "src_ip", "dst_ip", "src_port", "dst_port",
		"protocol", "ics_protocol", "payload_size", "payload_hex",
	}

	for _, field := range expectedFields {
		if _, ok := raw[field]; !ok {
			t.Errorf("missing JSON field: %s", field)
		}
	}
}

func TestICSProtocolDetectionFromDstPort(t *testing.T) {
	tests := []struct {
		name        string
		dstPort     uint16
		srcPort     uint16
		expectedICS string
	}{
		{
			name:        "Modbus on dst port",
			dstPort:     502,
			srcPort:     49152,
			expectedICS: "modbus",
		},
		{
			name:        "DNP3 on dst port",
			dstPort:     20000,
			srcPort:     49153,
			expectedICS: "dnp3",
		},
		{
			name:        "OPC-UA on dst port",
			dstPort:     4840,
			srcPort:     49154,
			expectedICS: "opcua",
		},
		{
			name:        "EtherNet/IP on dst port",
			dstPort:     44818,
			srcPort:     49155,
			expectedICS: "ethernet_ip",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			icsProtocol := types.ProtocolFromPort(tt.dstPort)
			if icsProtocol == "unknown" {
				icsProtocol = types.ProtocolFromPort(tt.srcPort)
			}
			if icsProtocol != tt.expectedICS {
				t.Errorf("ICS protocol = %s, want %s", icsProtocol, tt.expectedICS)
			}
		})
	}
}

func TestICSProtocolDetectionFromSrcPort(t *testing.T) {
	tests := []struct {
		name        string
		dstPort     uint16
		srcPort     uint16
		expectedICS string
	}{
		{
			name:        "Modbus response (src port is ICS)",
			dstPort:     49152,
			srcPort:     502,
			expectedICS: "modbus",
		},
		{
			name:        "DNP3 response",
			dstPort:     49153,
			srcPort:     20000,
			expectedICS: "dnp3",
		},
		{
			name:        "OPC-UA response",
			dstPort:     49154,
			srcPort:     4840,
			expectedICS: "opcua",
		},
		{
			name:        "EtherNet/IP response",
			dstPort:     49155,
			srcPort:     44818,
			expectedICS: "ethernet_ip",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			icsProtocol := types.ProtocolFromPort(tt.dstPort)
			if icsProtocol == "unknown" {
				icsProtocol = types.ProtocolFromPort(tt.srcPort)
			}
			if icsProtocol != tt.expectedICS {
				t.Errorf("ICS protocol = %s, want %s", icsProtocol, tt.expectedICS)
			}
		})
	}
}

func TestICSProtocolDetectionUnknown(t *testing.T) {
	dstPort := uint16(8080)
	srcPort := uint16(49156)

	icsProtocol := types.ProtocolFromPort(dstPort)
	if icsProtocol == "unknown" {
		icsProtocol = types.ProtocolFromPort(srcPort)
	}

	if icsProtocol != "unknown" {
		t.Errorf("ICS protocol = %s, want unknown", icsProtocol)
	}
}

func TestPacketMessageKeyGeneration(t *testing.T) {
	packet := &types.RawPacket{
		Timestamp:   time.Now(),
		SrcIP:       "192.168.1.100",
		DstIP:       "192.168.1.200",
		SrcPort:     49152,
		DstPort:     502,
		Protocol:    "tcp",
		PayloadSize: 0,
	}

	expectedKey := "192.168.1.100:192.168.1.200"
	actualKey := packet.SrcIP + ":" + packet.DstIP

	if actualKey != expectedKey {
		t.Errorf("key = %s, want %s", actualKey, expectedKey)
	}
}

func TestPacketMessageTimestampFormat(t *testing.T) {
	ts := time.Date(2024, 1, 15, 10, 30, 0, 123456789, time.UTC)
	formatted := ts.UTC().Format(time.RFC3339Nano)

	expected := "2024-01-15T10:30:00.123456789Z"
	if formatted != expected {
		t.Errorf("timestamp = %s, want %s", formatted, expected)
	}
}

func TestProducerConfigFields(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.KafkaConfig{
		Brokers:         []string{"localhost:9092"},
		Topic:           "ics.raw.packets",
		BatchSize:       100,
		BatchTimeoutMs:  50,
		CompressionType: "gzip",
	}

	producer, err := NewProducer(cfg, logger)
	if err != nil {
		t.Fatalf("NewProducer() error = %v", err)
	}
	defer func() { _ = producer.Close() }()

	if producer.config.Topic != cfg.Topic {
		t.Errorf("config.Topic = %s, want %s", producer.config.Topic, cfg.Topic)
	}
	if producer.config.BatchSize != cfg.BatchSize {
		t.Errorf("config.BatchSize = %d, want %d", producer.config.BatchSize, cfg.BatchSize)
	}
	if producer.config.BatchTimeoutMs != cfg.BatchTimeoutMs {
		t.Errorf("config.BatchTimeoutMs = %d, want %d", producer.config.BatchTimeoutMs, cfg.BatchTimeoutMs)
	}
	if producer.config.CompressionType != cfg.CompressionType {
		t.Errorf("config.CompressionType = %s, want %s", producer.config.CompressionType, cfg.CompressionType)
	}
}

func TestPacketMessageEmptyPayload(t *testing.T) {
	msg := PacketMessage{
		Timestamp:   "2024-01-15T10:30:00Z",
		SrcIP:       "10.0.0.1",
		DstIP:       "10.0.0.2",
		SrcPort:     12345,
		DstPort:     502,
		Protocol:    "tcp",
		ICSProtocol: "modbus",
		PayloadSize: 0,
		PayloadHex:  "",
	}

	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("json.Marshal() error = %v", err)
	}

	var decoded PacketMessage
	err = json.Unmarshal(data, &decoded)
	if err != nil {
		t.Fatalf("json.Unmarshal() error = %v", err)
	}

	if decoded.PayloadSize != 0 {
		t.Errorf("PayloadSize = %d, want 0", decoded.PayloadSize)
	}
	if decoded.PayloadHex != "" {
		t.Errorf("PayloadHex = %s, want empty", decoded.PayloadHex)
	}
}
