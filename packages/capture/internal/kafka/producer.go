// Package kafka provides Kafka producer functionality for publishing captured packets.
package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/caverac/ics-anomaly-detection/packages/capture/internal/config"
	"github.com/caverac/ics-anomaly-detection/packages/capture/pkg/types"
	"github.com/segmentio/kafka-go"
	"github.com/segmentio/kafka-go/compress"
	"go.uber.org/zap"
)

// Producer handles publishing packets to Kafka
type Producer struct {
	config config.KafkaConfig
	writer *kafka.Writer
	logger *zap.Logger
}

// NewProducer creates a new Kafka producer
func NewProducer(cfg config.KafkaConfig, logger *zap.Logger) (*Producer, error) {
	// Determine compression type
	var compression kafka.Compression
	switch cfg.CompressionType {
	case "gzip":
		compression = compress.Gzip
	case "snappy":
		compression = compress.Snappy
	case "lz4":
		compression = compress.Lz4
	case "zstd":
		compression = compress.Zstd
	default:
		compression = 0 // No compression
	}

	writer := &kafka.Writer{
		Addr:         kafka.TCP(cfg.Brokers...),
		Topic:        cfg.Topic,
		Balancer:     &kafka.Hash{}, // Partition by key
		BatchSize:    cfg.BatchSize,
		BatchTimeout: time.Duration(cfg.BatchTimeoutMs) * time.Millisecond,
		Compression:  compression,
		Async:        true, // Async for higher throughput
		RequiredAcks: kafka.RequireOne,
	}

	logger.Info("kafka producer created",
		zap.Strings("brokers", cfg.Brokers),
		zap.String("topic", cfg.Topic),
		zap.Int("batch_size", cfg.BatchSize),
	)

	return &Producer{
		config: cfg,
		writer: writer,
		logger: logger,
	}, nil
}

// Close closes the Kafka writer
func (p *Producer) Close() error {
	if p.writer != nil {
		return p.writer.Close()
	}
	return nil
}

// Publish sends a packet to Kafka
func (p *Producer) Publish(ctx context.Context, packet *types.RawPacket) error {
	// Create message key from src:dst IP pair for consistent partitioning
	key := fmt.Sprintf("%s:%s", packet.SrcIP, packet.DstIP)

	// Determine ICS protocol from port
	icsProtocol := types.ProtocolFromPort(packet.DstPort)
	if icsProtocol == "unknown" {
		icsProtocol = types.ProtocolFromPort(packet.SrcPort)
	}

	// Create message payload
	msg := PacketMessage{
		Timestamp:   packet.Timestamp.UTC().Format(time.RFC3339Nano),
		SrcIP:       packet.SrcIP,
		DstIP:       packet.DstIP,
		SrcPort:     packet.SrcPort,
		DstPort:     packet.DstPort,
		Protocol:    packet.Protocol,
		ICSProtocol: icsProtocol,
		PayloadSize: packet.PayloadSize,
		PayloadHex:  packet.PayloadHex,
	}

	value, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("failed to marshal packet: %w", err)
	}

	return p.writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(key),
		Value: value,
		Headers: []kafka.Header{
			{Key: "ics_protocol", Value: []byte(icsProtocol)},
			{Key: "capture_time", Value: []byte(packet.Timestamp.UTC().Format(time.RFC3339))},
		},
	})
}

// PublishBatch sends multiple packets to Kafka
func (p *Producer) PublishBatch(ctx context.Context, packets []*types.RawPacket) error {
	messages := make([]kafka.Message, 0, len(packets))

	for _, packet := range packets {
		key := fmt.Sprintf("%s:%s", packet.SrcIP, packet.DstIP)

		icsProtocol := types.ProtocolFromPort(packet.DstPort)
		if icsProtocol == "unknown" {
			icsProtocol = types.ProtocolFromPort(packet.SrcPort)
		}

		msg := PacketMessage{
			Timestamp:   packet.Timestamp.UTC().Format(time.RFC3339Nano),
			SrcIP:       packet.SrcIP,
			DstIP:       packet.DstIP,
			SrcPort:     packet.SrcPort,
			DstPort:     packet.DstPort,
			Protocol:    packet.Protocol,
			ICSProtocol: icsProtocol,
			PayloadSize: packet.PayloadSize,
			PayloadHex:  packet.PayloadHex,
		}

		value, err := json.Marshal(msg)
		if err != nil {
			p.logger.Warn("failed to marshal packet", zap.Error(err))
			continue
		}

		messages = append(messages, kafka.Message{
			Key:   []byte(key),
			Value: value,
			Headers: []kafka.Header{
				{Key: "ics_protocol", Value: []byte(icsProtocol)},
			},
		})
	}

	if len(messages) == 0 {
		return nil
	}

	return p.writer.WriteMessages(ctx, messages...)
}

// PacketMessage is the JSON structure sent to Kafka
type PacketMessage struct {
	Timestamp   string `json:"timestamp"`
	SrcIP       string `json:"src_ip"`
	DstIP       string `json:"dst_ip"`
	SrcPort     uint16 `json:"src_port"`
	DstPort     uint16 `json:"dst_port"`
	Protocol    string `json:"protocol"`
	ICSProtocol string `json:"ics_protocol"`
	PayloadSize int    `json:"payload_size"`
	PayloadHex  string `json:"payload_hex"`
}
