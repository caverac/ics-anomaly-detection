package types

import (
	"testing"
)

func TestProtocolFromPort(t *testing.T) {
	tests := []struct {
		name     string
		port     uint16
		expected string
	}{
		{
			name:     "Modbus TCP port",
			port:     PortModbusTCP,
			expected: "modbus",
		},
		{
			name:     "DNP3 port",
			port:     PortDNP3,
			expected: "dnp3",
		},
		{
			name:     "OPC-UA port",
			port:     PortOPCUA,
			expected: "opcua",
		},
		{
			name:     "EtherNet/IP port",
			port:     PortEtherNetIP,
			expected: "ethernet_ip",
		},
		{
			name:     "Unknown port",
			port:     8080,
			expected: "unknown",
		},
		{
			name:     "Zero port",
			port:     0,
			expected: "unknown",
		},
		{
			name:     "HTTP port",
			port:     80,
			expected: "unknown",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := ProtocolFromPort(tt.port)
			if result != tt.expected {
				t.Errorf("ProtocolFromPort(%d) = %s, want %s", tt.port, result, tt.expected)
			}
		})
	}
}

func TestPortConstants(t *testing.T) {
	// Verify port constants are correct
	if PortModbusTCP != 502 {
		t.Errorf("PortModbusTCP = %d, want 502", PortModbusTCP)
	}
	if PortDNP3 != 20000 {
		t.Errorf("PortDNP3 = %d, want 20000", PortDNP3)
	}
	if PortOPCUA != 4840 {
		t.Errorf("PortOPCUA = %d, want 4840", PortOPCUA)
	}
	if PortEtherNetIP != 44818 {
		t.Errorf("PortEtherNetIP = %d, want 44818", PortEtherNetIP)
	}
}

func TestRawPacketFields(t *testing.T) {
	// Test that RawPacket struct can be instantiated with all fields
	packet := RawPacket{
		SrcIP:       "192.168.1.1",
		DstIP:       "192.168.1.2",
		SrcPort:     49152,
		DstPort:     502,
		Protocol:    "tcp",
		PayloadSize: 12,
		Payload:     []byte{0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x01, 0x03, 0x00, 0x00, 0x00, 0x0a},
		PayloadHex:  "000100000006010300000a",
	}

	if packet.SrcIP != "192.168.1.1" {
		t.Errorf("SrcIP = %s, want 192.168.1.1", packet.SrcIP)
	}
	if packet.DstPort != 502 {
		t.Errorf("DstPort = %d, want 502", packet.DstPort)
	}
	if packet.PayloadSize != 12 {
		t.Errorf("PayloadSize = %d, want 12", packet.PayloadSize)
	}
}

func TestCaptureStatsFields(t *testing.T) {
	stats := CaptureStats{
		PacketsCaptured:  1000,
		PacketsDropped:   5,
		BytesCaptured:    50000,
		PacketsFiltered:  100,
		PacketsPublished: 895,
		ErrorCount:       2,
	}

	if stats.PacketsCaptured != 1000 {
		t.Errorf("PacketsCaptured = %d, want 1000", stats.PacketsCaptured)
	}
	if stats.PacketsDropped != 5 {
		t.Errorf("PacketsDropped = %d, want 5", stats.PacketsDropped)
	}
	if stats.PacketsPublished != 895 {
		t.Errorf("PacketsPublished = %d, want 895", stats.PacketsPublished)
	}
}
