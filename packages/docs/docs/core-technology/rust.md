# Rust

Rust is used for the **parser** service, which decodes binary ICS protocol payloads (Modbus, DNP3, OPC-UA) into structured data.

## Why Rust?

### Memory safety without garbage collection

Parsing untrusted binary data from network traffic is security-sensitive. Rust's ownership system prevents:

- Buffer overflows
- Use-after-free
- Data races

This is critical when parsing potentially malformed or malicious packets.

### Zero-cost abstractions

Rust's abstractions compile away, giving C-like performance. Protocol parsing involves many small operations (bit manipulation, bounds checking) where overhead matters.

### Excellent parser combinator ecosystem

The `nom` library provides:

- Composable binary parsers
- Zero-copy parsing
- Compile-time parser validation
- Excellent error messages

### Fearless concurrency

Rust's type system prevents data races at compile time, making concurrent Kafka consumption safe and efficient.

### No runtime overhead

No garbage collector pauses or JIT warmup. Consistent, predictable latency for real-time processing.

## Alternatives considered

| Alternative            | Pros                                    | Cons                                                        |
| ---------------------- | --------------------------------------- | ----------------------------------------------------------- |
| **C**                  | Maximum control, existing ICS libraries | Memory safety issues, no modern tooling                     |
| **C++**                | Better abstractions than C              | Still manual memory management, complex                     |
| **Go**                 | Simpler, faster compilation             | Less suitable for complex binary parsing, no nom equivalent |
| **Python (construct)** | Rapid prototyping                       | Too slow for production parsing, GIL                        |

## Limitations

### Steep learning curve

Rust's ownership model, lifetimes, and borrow checker take time to learn. New contributors may struggle initially.

### Longer compilation times

Rust's compile times are longer than Go or C. Incremental builds help, but clean builds take several minutes.

### Smaller ecosystem

While growing rapidly, Rust's ecosystem is smaller than Python or JavaScript. Some ICS-specific libraries don't exist yet.

### Async complexity

Async Rust (`async`/`await`) has a learning curve. Understanding `Pin`, `Future`, and async runtimes requires effort.

### Limited ICS protocol libraries

Unlike Python (which has `pymodbus`, `pydnp3`), Rust has fewer ready-made ICS libraries. We wrote custom parsers using `nom`.

## Usage in this project

```
packages/parser/
├── src/
│   ├── main.rs              # Entry point, Kafka loop
│   ├── config/              # Configuration
│   ├── kafka/               # Consumer/producer
│   └── protocols/
│       ├── modbus.rs        # Modbus TCP parser
│       ├── dnp3.rs          # DNP3 parser
│       └── opcua.rs         # OPC-UA parser
└── Cargo.toml
```

## Key dependencies

| Crate     | Purpose                                 |
| --------- | --------------------------------------- |
| `nom`     | Parser combinators for binary protocols |
| `rdkafka` | Kafka client (librdkafka wrapper)       |
| `tokio`   | Async runtime                           |
| `axum`    | HTTP server for metrics                 |
| `serde`   | Serialization/deserialization           |
| `tracing` | Structured logging                      |

## Parser example

```rust
use nom::{number::complete::be_u16, IResult};

fn parse_mbap_header(input: &[u8]) -> IResult<&[u8], MbapHeader> {
    let (input, transaction_id) = be_u16(input)?;
    let (input, protocol_id) = be_u16(input)?;
    let (input, length) = be_u16(input)?;
    let (input, unit_id) = be_u8(input)?;
    Ok((input, MbapHeader { transaction_id, protocol_id, length, unit_id }))
}
```
