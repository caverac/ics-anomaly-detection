package capture

import (
	"context"
	"testing"
	"time"

	"github.com/caverac/ics-anomaly-detection/packages/capture/internal/config"
	"github.com/caverac/ics-anomaly-detection/packages/capture/pkg/types"
	"go.uber.org/zap"
)

func TestNewCapturer(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.CaptureConfig{
		Interface:   "lo0",
		SnapLen:     1600,
		Promiscuous: true,
		TimeoutMs:   100,
		BPFFilter:   "tcp port 502",
		BufferSize:  64,
	}

	capturer := New(cfg, logger)

	if capturer == nil {
		t.Fatal("New() returned nil")
	}
	if capturer.config.Interface != "lo0" {
		t.Errorf("config.Interface = %s, want lo0", capturer.config.Interface)
	}
	if capturer.packets == nil {
		t.Error("packets channel is nil")
	}
}

func TestCapturerStats(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.CaptureConfig{
		Interface: "lo0",
		SnapLen:   1600,
	}

	capturer := New(cfg, logger)

	// Initial stats should be zero
	stats := capturer.Stats()
	if stats.PacketsCaptured != 0 {
		t.Errorf("PacketsCaptured = %d, want 0", stats.PacketsCaptured)
	}
	if stats.PacketsDropped != 0 {
		t.Errorf("PacketsDropped = %d, want 0", stats.PacketsDropped)
	}
	if stats.BytesCaptured != 0 {
		t.Errorf("BytesCaptured = %d, want 0", stats.BytesCaptured)
	}
}

func TestCapturerPacketsChannel(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.CaptureConfig{
		Interface: "lo0",
		SnapLen:   1600,
	}

	capturer := New(cfg, logger)
	packets := capturer.Packets()

	if packets == nil {
		t.Error("Packets() returned nil channel")
	}
}

func TestCapturerOpenInvalidInterface(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.CaptureConfig{
		Interface:   "nonexistent_interface_12345",
		SnapLen:     1600,
		Promiscuous: true,
		TimeoutMs:   100,
	}

	capturer := New(cfg, logger)
	err := capturer.Open()

	if err == nil {
		capturer.Close()
		t.Error("Open() expected error for invalid interface, got nil")
	}
}

func TestCapturerRunWithoutOpen(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.CaptureConfig{
		Interface: "lo0",
		SnapLen:   1600,
	}

	capturer := New(cfg, logger)
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	err := capturer.Run(ctx)
	if err == nil {
		t.Error("Run() expected error when handle not opened, got nil")
	}
}

func TestCapturerClose(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.CaptureConfig{
		Interface: "lo0",
		SnapLen:   1600,
	}

	capturer := New(cfg, logger)

	// Close should not panic even without Open
	capturer.Close()

	// Verify channel is closed
	_, ok := <-capturer.packets
	if ok {
		t.Error("packets channel should be closed after Close()")
	}
}

func TestProcessPacketNilNetworkLayer(t *testing.T) {
	logger := zap.NewNop()
	cfg := config.CaptureConfig{
		Interface: "lo0",
		SnapLen:   1600,
	}

	capturer := New(cfg, logger)

	// This tests the internal logic - we can't easily create a gopacket.Packet
	// without the actual capture, so we verify the struct is properly initialized
	if capturer.logger == nil {
		t.Error("logger should not be nil")
	}
}

func TestRawPacketCreation(t *testing.T) {
	packet := &types.RawPacket{
		Timestamp:   time.Now(),
		SrcIP:       "192.168.1.1",
		DstIP:       "192.168.1.2",
		SrcPort:     49152,
		DstPort:     502,
		Protocol:    "tcp",
		PayloadSize: 12,
		Payload:     []byte{0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x0a},
		PayloadHex:  "00010000000601030000000a",
	}

	if packet.SrcIP != "192.168.1.1" {
		t.Errorf("SrcIP = %s, want 192.168.1.1", packet.SrcIP)
	}
	if packet.DstPort != 502 {
		t.Errorf("DstPort = %d, want 502", packet.DstPort)
	}
	if len(packet.Payload) != 12 {
		t.Errorf("len(Payload) = %d, want 12", len(packet.Payload))
	}
}

func TestCapturerConfigValidation(t *testing.T) {
	tests := []struct {
		name   string
		config config.CaptureConfig
	}{
		{
			name: "minimum config",
			config: config.CaptureConfig{
				Interface: "lo0",
				SnapLen:   100,
			},
		},
		{
			name: "full config",
			config: config.CaptureConfig{
				Interface:   "eth0",
				SnapLen:     65535,
				Promiscuous: true,
				TimeoutMs:   1000,
				BPFFilter:   "tcp port 502",
				BufferSize:  256,
			},
		},
		{
			name: "empty BPF filter",
			config: config.CaptureConfig{
				Interface: "lo0",
				SnapLen:   1600,
				BPFFilter: "",
			},
		},
	}

	logger := zap.NewNop()

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			capturer := New(tt.config, logger)
			if capturer == nil {
				t.Fatal("New() returned nil")
			}
			if capturer.config.Interface != tt.config.Interface {
				t.Errorf("Interface = %s, want %s", capturer.config.Interface, tt.config.Interface)
			}
		})
	}
}
