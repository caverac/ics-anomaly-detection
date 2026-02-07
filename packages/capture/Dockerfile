# Build stage
FROM golang:1.23-alpine AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libpcap-dev

WORKDIR /app

# Copy go mod files and download dependencies
COPY go.mod ./
RUN go mod download && go mod tidy

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=1 GOOS=linux go build -ldflags="-s -w" -o /capture ./cmd/capture

# Runtime stage
FROM alpine:3.19

# Install runtime dependencies
RUN apk add --no-cache libpcap ca-certificates tzdata

# Create non-root user
RUN addgroup -S capture && adduser -S capture -G capture

WORKDIR /app

# Copy binary from builder
COPY --from=builder /capture .
COPY config.yaml .

# Note: Running as root is required for packet capture
# In production, use capabilities instead: setcap cap_net_raw,cap_net_admin=eip /app/capture

EXPOSE 8081

ENTRYPOINT ["/app/capture"]
CMD ["-config", "/app/config.yaml"]
