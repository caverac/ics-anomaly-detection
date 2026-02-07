// Package capture provides packet capture functionality for ICS network traffic.
package capture

import (
	"context"
	"encoding/hex"
	"fmt"
	"sync/atomic"
	"time"

	"github.com/caverac/ics-anomaly-detection/packages/capture/internal/config"
	"github.com/caverac/ics-anomaly-detection/packages/capture/pkg/types"
	"github.com/google/gopacket"
	"github.com/google/gopacket/layers"
	"github.com/google/gopacket/pcap"
	"go.uber.org/zap"
)

// Capturer handles packet capture from a network interface
type Capturer struct {
	config  config.CaptureConfig
	handle  *pcap.Handle
	logger  *zap.Logger
	stats   types.CaptureStats
	packets chan *types.RawPacket
}

// New creates a new Capturer instance
func New(cfg config.CaptureConfig, logger *zap.Logger) *Capturer {
	return &Capturer{
		config:  cfg,
		logger:  logger,
		packets: make(chan *types.RawPacket, 10000), // Buffer for backpressure
	}
}

// Open initializes the packet capture handle
func (c *Capturer) Open() error {
	// Check if interface exists
	devices, err := pcap.FindAllDevs()
	if err != nil {
		return fmt.Errorf("failed to list interfaces: %w", err)
	}

	found := false
	for _, d := range devices {
		if d.Name == c.config.Interface {
			found = true
			break
		}
	}
	if !found {
		c.logger.Warn("interface not found, listing available interfaces")
		for _, d := range devices {
			c.logger.Info("available interface", zap.String("name", d.Name), zap.String("description", d.Description))
		}
		return fmt.Errorf("interface %s not found", c.config.Interface)
	}

	// Open the interface
	inactive, err := pcap.NewInactiveHandle(c.config.Interface)
	if err != nil {
		return fmt.Errorf("failed to create inactive handle: %w", err)
	}
	defer inactive.CleanUp()

	if err := inactive.SetSnapLen(int(c.config.SnapLen)); err != nil {
		return fmt.Errorf("failed to set snap length: %w", err)
	}

	if err := inactive.SetPromisc(c.config.Promiscuous); err != nil {
		return fmt.Errorf("failed to set promiscuous mode: %w", err)
	}

	if err := inactive.SetTimeout(time.Duration(c.config.TimeoutMs) * time.Millisecond); err != nil {
		return fmt.Errorf("failed to set timeout: %w", err)
	}

	if c.config.BufferSize > 0 {
		if err := inactive.SetBufferSize(c.config.BufferSize * 1024 * 1024); err != nil {
			return fmt.Errorf("failed to set buffer size: %w", err)
		}
	}

	handle, err := inactive.Activate()
	if err != nil {
		return fmt.Errorf("failed to activate handle: %w", err)
	}

	// Set BPF filter
	if c.config.BPFFilter != "" {
		if err := handle.SetBPFFilter(c.config.BPFFilter); err != nil {
			handle.Close()
			return fmt.Errorf("failed to set BPF filter: %w", err)
		}
		c.logger.Info("BPF filter applied", zap.String("filter", c.config.BPFFilter))
	}

	c.handle = handle
	c.logger.Info("capture handle opened",
		zap.String("interface", c.config.Interface),
		zap.Int32("snap_len", c.config.SnapLen),
		zap.Bool("promiscuous", c.config.Promiscuous),
	)

	return nil
}

// Close releases the capture handle
func (c *Capturer) Close() {
	if c.handle != nil {
		c.handle.Close()
	}
	close(c.packets)
}

// Packets returns the channel of captured packets
func (c *Capturer) Packets() <-chan *types.RawPacket {
	return c.packets
}

// Stats returns current capture statistics
func (c *Capturer) Stats() types.CaptureStats {
	return types.CaptureStats{
		PacketsCaptured:  atomic.LoadUint64(&c.stats.PacketsCaptured),
		PacketsDropped:   atomic.LoadUint64(&c.stats.PacketsDropped),
		BytesCaptured:    atomic.LoadUint64(&c.stats.BytesCaptured),
		PacketsFiltered:  atomic.LoadUint64(&c.stats.PacketsFiltered),
		PacketsPublished: atomic.LoadUint64(&c.stats.PacketsPublished),
		ErrorCount:       atomic.LoadUint64(&c.stats.ErrorCount),
	}
}

// Run starts the capture loop
func (c *Capturer) Run(ctx context.Context) error {
	if c.handle == nil {
		return fmt.Errorf("capture handle not opened")
	}

	packetSource := gopacket.NewPacketSource(c.handle, c.handle.LinkType())
	packetSource.NoCopy = true

	c.logger.Info("starting packet capture")

	for {
		select {
		case <-ctx.Done():
			c.logger.Info("capture stopped", zap.Error(ctx.Err()))
			return ctx.Err()

		case packet, ok := <-packetSource.Packets():
			if !ok {
				return fmt.Errorf("packet source closed")
			}

			atomic.AddUint64(&c.stats.PacketsCaptured, 1)

			rawPacket := c.processPacket(packet)
			if rawPacket == nil {
				// Packet filtered out
				atomic.AddUint64(&c.stats.PacketsFiltered, 1)
				continue
			}

			// #nosec G115 - PayloadSize is bounded by snap_len which is at most 65535
			atomic.AddUint64(&c.stats.BytesCaptured, uint64(rawPacket.PayloadSize))

			// Non-blocking send to channel
			select {
			case c.packets <- rawPacket:
				atomic.AddUint64(&c.stats.PacketsPublished, 1)
			default:
				// Channel full, drop packet
				atomic.AddUint64(&c.stats.PacketsDropped, 1)
				c.logger.Warn("packet buffer full, dropping packet")
			}
		}
	}
}

// processPacket extracts relevant information from a captured packet
func (c *Capturer) processPacket(packet gopacket.Packet) *types.RawPacket {
	// Get timestamp
	metadata := packet.Metadata()
	timestamp := metadata.Timestamp
	if timestamp.IsZero() {
		timestamp = time.Now()
	}

	// Extract network layer (IP)
	networkLayer := packet.NetworkLayer()
	if networkLayer == nil {
		return nil // Not an IP packet
	}

	var srcIP, dstIP string
	switch nl := networkLayer.(type) {
	case *layers.IPv4:
		srcIP = nl.SrcIP.String()
		dstIP = nl.DstIP.String()
	case *layers.IPv6:
		srcIP = nl.SrcIP.String()
		dstIP = nl.DstIP.String()
	default:
		return nil
	}

	// Extract transport layer (TCP/UDP)
	transportLayer := packet.TransportLayer()
	if transportLayer == nil {
		return nil
	}

	var srcPort, dstPort uint16
	var protocol string

	switch tl := transportLayer.(type) {
	case *layers.TCP:
		srcPort = uint16(tl.SrcPort)
		dstPort = uint16(tl.DstPort)
		protocol = "tcp"
	case *layers.UDP:
		srcPort = uint16(tl.SrcPort)
		dstPort = uint16(tl.DstPort)
		protocol = "udp"
	default:
		return nil
	}

	// Get application layer payload
	appLayer := packet.ApplicationLayer()
	if appLayer == nil {
		return nil // No payload
	}

	payload := appLayer.Payload()
	if len(payload) == 0 {
		return nil
	}

	return &types.RawPacket{
		Timestamp:   timestamp,
		SrcIP:       srcIP,
		DstIP:       dstIP,
		SrcPort:     srcPort,
		DstPort:     dstPort,
		Protocol:    protocol,
		PayloadSize: len(payload),
		Payload:     payload,
		PayloadHex:  hex.EncodeToString(payload),
	}
}
