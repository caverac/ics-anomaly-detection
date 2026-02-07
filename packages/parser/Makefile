.PHONY: build run test clean fmt lint check coverage coverage-html verify

BINARY_NAME=ics-parser

all: build

build:
	cargo build --release

build-debug:
	cargo build

run:
	RUST_LOG=debug cargo run

run-release:
	RUST_LOG=info ./target/release/$(BINARY_NAME)

test:
	cargo test

test-verbose:
	cargo test -- --nocapture

# Run tests with coverage (requires cargo-tarpaulin)
coverage:
	cargo tarpaulin --skip-clean 2>/dev/null || (echo "Install tarpaulin: cargo install cargo-tarpaulin" && exit 1)
	@echo ""
	@echo "=== Coverage Summary ==="

coverage-html:
	mkdir -p coverage
	cargo tarpaulin --out Html --output-dir coverage
	@echo "Coverage report generated: coverage/tarpaulin-report.html"

clean:
	cargo clean
	rm -rf coverage

fmt:
	cargo fmt

fmt-check:
	cargo fmt -- --check

lint:
	cargo clippy -- -D warnings

lint-pedantic:
	cargo clippy -- -D warnings -W clippy::pedantic

check:
	cargo check

# Run all checks (format, lint, test)
verify: fmt-check lint test
	@echo ""
	@echo "=== All checks passed ==="

# Install development dependencies
install-dev-deps:
	rustup component add clippy rustfmt
	cargo install cargo-tarpaulin

# Install dependencies (macOS)
install-deps-macos:
	brew install cmake openssl pkg-config

# Install dependencies (Ubuntu)
install-deps-ubuntu:
	sudo apt-get update && sudo apt-get install -y \
		build-essential \
		cmake \
		libssl-dev \
		pkg-config \
		libsasl2-dev

# Docker build
docker-build:
	docker build -t ics-parser:latest .

# Generate documentation
docs:
	cargo doc --open

# Check for security vulnerabilities (requires cargo-audit)
audit:
	cargo audit

# Update dependencies
update:
	cargo update
