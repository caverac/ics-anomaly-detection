// Package types provides common data structures for the ICS capture service.
package types

import "time"

// RawPacket represents a captured network packet ready for parsing
type RawPacket struct {
	Timestamp   time.Time `json:"timestamp"`
	SrcIP       string    `json:"src_ip"`
	DstIP       string    `json:"dst_ip"`
	SrcPort     uint16    `json:"src_port"`
	DstPort     uint16    `json:"dst_port"`
	Protocol    string    `json:"protocol"` // tcp or udp
	PayloadSize int       `json:"payload_size"`
	Payload     []byte    `json:"payload"`     // Raw payload bytes
	PayloadHex  string    `json:"payload_hex"` // Hex-encoded payload
}

// CaptureStats holds capture statistics
type CaptureStats struct {
	PacketsCaptured  uint64 `json:"packets_captured"`
	PacketsDropped   uint64 `json:"packets_dropped"`
	BytesCaptured    uint64 `json:"bytes_captured"`
	PacketsFiltered  uint64 `json:"packets_filtered"`
	PacketsPublished uint64 `json:"packets_published"`
	ErrorCount       uint64 `json:"error_count"`
}

// ICS protocol port constants
const (
	PortModbusTCP  = 502
	PortDNP3       = 20000
	PortOPCUA      = 4840
	PortEtherNetIP = 44818
)

// ProtocolFromPort determines the likely ICS protocol from port number
func ProtocolFromPort(port uint16) string {
	switch port {
	case PortModbusTCP:
		return "modbus"
	case PortDNP3:
		return "dnp3"
	case PortOPCUA:
		return "opcua"
	case PortEtherNetIP:
		return "ethernet_ip"
	default:
		return "unknown"
	}
}
