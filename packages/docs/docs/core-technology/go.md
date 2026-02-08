# Go

Go is used for the **capture** service, which performs raw network packet capture from network interfaces.

## Why Go?

### Performance with simplicity
Go provides near-C performance while maintaining readable, maintainable code. For packet capture at high throughput (thousands of packets/second), this balance is critical.

### Excellent concurrency model
Go's goroutines and channels make it natural to:
- Capture packets in one goroutine
- Process and batch them in another
- Publish to Kafka asynchronously

This maps perfectly to the capture service's architecture.

### Native libpcap bindings
The `gopacket` library provides mature, well-tested bindings to libpcap with:
- Zero-copy packet access
- Built-in protocol dissection
- BPF filter support

### Single binary deployment
Go compiles to a single static binary with no runtime dependencies (except libpcap). This simplifies Docker images and deployment.

### Strong standard library
The `net/http` package provides a production-ready HTTP server for health checks and metrics without external dependencies.

## Alternatives considered

| Alternative | Pros | Cons |
|-------------|------|------|
| **C/C++** | Maximum performance, direct libpcap access | Memory safety concerns, slower development, complex build systems |
| **Rust** | Memory safety, zero-cost abstractions | Steeper learning curve, less mature pcap ecosystem at the time |
| **Python (Scapy)** | Rapid development, flexible | Too slow for high-throughput capture, GIL limitations |
| **Java** | Mature ecosystem | JVM startup time, memory overhead, less suitable for system-level work |

## Limitations

### CGO dependency
The `gopacket` library requires CGO for libpcap bindings, which:
- Complicates cross-compilation
- Requires libpcap-dev in the build environment
- Slightly increases binary size

### No generics (historically)
Go 1.18+ added generics, but the codebase was started before this. Some code uses interface{} where generics would be cleaner.

### Error handling verbosity
Go's explicit error handling (`if err != nil`) is verbose compared to Rust's `?` operator or exceptions. However, this makes error paths explicit and visible.

### Limited protocol parsing
While `gopacket` handles network layers well, it doesn't parse application-layer ICS protocols (Modbus, DNP3). This is why we delegate parsing to the Rust service.

## Usage in this project

```
packages/capture/
├── cmd/capture/main.go      # Entry point
├── internal/
│   ├── capture/             # gopacket wrapper
│   ├── config/              # Configuration
│   └── kafka/               # Kafka producer
└── pkg/types/               # Shared types
```

## Key dependencies

| Package | Purpose |
|---------|---------|
| `github.com/google/gopacket` | Packet capture and dissection |
| `github.com/confluentinc/confluent-kafka-go` | Kafka producer |
| `go.uber.org/zap` | Structured logging |
