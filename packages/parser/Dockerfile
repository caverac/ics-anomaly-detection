# Build stage
FROM rust:1.83-bookworm AS builder

# Install build dependencies for rdkafka
RUN apt-get update && apt-get install -y \
    cmake \
    libssl-dev \
    libsasl2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy manifests
COPY Cargo.toml ./

# Create dummy source to cache dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Copy actual source code
COPY src ./src

# Build the application (touch to invalidate cache)
RUN touch src/main.rs && cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libsasl2-2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -r -s /bin/false parser

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/ics-parser .
COPY config.toml .

# Use non-root user
USER parser

EXPOSE 8082

ENV RUST_LOG=info

ENTRYPOINT ["/app/ics-parser"]
