.PHONY: help up down logs clean build test dev dev-full dev-alerting dev-dashboard e2e-test all start

# =============================================================================
# Help
# =============================================================================

help:
	@echo "ICS Anomaly Detection"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "=== Infrastructure (Docker) ==="
	@echo "  up              Start core infrastructure (Kafka, Redis)"
	@echo "  down            Stop all services"
	@echo "  logs            Tail all logs"
	@echo "  clean           Remove all containers and volumes"
	@echo ""
	@echo "=== Development (Docker Compose) ==="
	@echo "  start / all     Start everything (alias for dev-dashboard)"
	@echo "  dev             Start simulator + parser + feature-engine"
	@echo "  dev-full        Add anomaly-detection"
	@echo "  dev-alerting    Add alerting service"
	@echo "  dev-dashboard   Add dashboard UI"
	@echo "  debug           Add Kafka UI for debugging"
	@echo ""
	@echo "=== Build (Docker Images) ==="
	@echo "  build           Build all Docker images"
	@echo "  build-<svc>     Build specific service (capture, parser, etc.)"
	@echo ""
	@echo "=== CI/CD (Docker-based) ==="
	@echo "  ci-lint         Lint all languages via Docker"
	@echo "  ci-test         Test all languages via Docker"
	@echo "  ci-build        Build all Docker images"
	@echo "  ci              Run full CI pipeline"
	@echo "  e2e-test        Run E2E pipeline tests"
	@echo ""
	@echo "=== Kafka Utilities ==="
	@echo "  kafka-topics    List Kafka topics"
	@echo "  kafka-consume-* Consume from specific topic"
	@echo ""
	@echo "=== Other ==="
	@echo "  train           Train ML models from Kafka data"
	@echo "  status          Show status of all services"
	@echo ""
	@echo "For JS/TS tasks (lint, format, typecheck), use yarn:"
	@echo "  yarn lint       Lint JS/TS code"
	@echo "  yarn build      Build docs + dashboard"
	@echo "  yarn ci         Full JS/TS CI pipeline"

# =============================================================================
# Infrastructure
# =============================================================================

up:
	docker compose up -d kafka redis
	@echo "Waiting for Kafka to be ready..."
	@sleep 10
	docker compose up -d kafka-init
	@echo ""
	@echo "Infrastructure ready:"
	@echo "  Kafka: localhost:9094"
	@echo "  Redis: localhost:6379"

down:
	docker compose --profile simulator --profile debug --profile monitoring down

logs:
	docker compose logs -f

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

status:
	@echo "=== Container Status ==="
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "=== Service Health ==="
	@for port in 8082 8083 8084 8085; do \
		status=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$$port/health 2>/dev/null || echo "down"); \
		echo "  :$$port → $$status"; \
	done

# =============================================================================
# Development Modes
# =============================================================================

dev: up
	docker compose --profile simulator up -d
	docker compose up -d parser feature-engine
	@echo ""
	@echo "Development environment ready!"
	@echo "  Simulator: http://localhost:8083"
	@echo ""
	@echo "Pipeline: Simulator → Parser → Feature Engine"

dev-full: up
	docker compose --profile simulator up -d
	docker compose up -d parser feature-engine anomaly-detection
	@echo ""
	@echo "Full pipeline ready!"
	@echo "  Simulator: http://localhost:8083"
	@echo "  Anomaly Detection: http://localhost:8085"
	@echo ""
	@echo "Pipeline: Simulator → Parser → Feature Engine → Anomaly Detection"

dev-alerting: up
	docker compose --profile simulator up -d
	docker compose up -d parser feature-engine anomaly-detection alerting
	@echo ""
	@echo "Pipeline with alerting ready!"
	@echo "  Simulator: http://localhost:8083"
	@echo "  Alerting API: http://localhost:8084"
	@echo ""
	@echo "Test attack: curl -X POST http://localhost:8083/attack/start -H 'Content-Type: application/json' -d '{\"mode\": \"reconnaissance\"}'"
	@echo "View alerts: curl http://localhost:8084/alerts"

dev-dashboard: up
	docker compose --profile simulator up -d
	docker compose up -d parser feature-engine anomaly-detection alerting dashboard
	@echo ""
	@echo "Full stack ready!"
	@echo "  Dashboard: http://localhost:3090"
	@echo "  Alerting API: http://localhost:8084"
	@echo "  Simulator: http://localhost:8083"

# Aliases for starting everything
all: dev-dashboard
start: dev-dashboard

debug: up
	docker compose --profile debug up -d
	@echo ""
	@echo "Debug tools:"
	@echo "  Kafka UI: http://localhost:8080"

monitoring: up
	docker compose --profile monitoring up -d
	@echo ""
	@echo "Monitoring:"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3001 (admin/admin)"

# =============================================================================
# Build (Docker Images)
# =============================================================================

build:
	docker compose build

build-capture:
	docker compose build capture

build-parser:
	docker compose build parser

build-simulator:
	docker compose build simulator

build-feature-engine:
	docker compose build feature-engine

build-anomaly-detection:
	docker compose build anomaly-detection

build-alerting:
	docker compose build alerting

build-dashboard:
	docker compose build dashboard

# =============================================================================
# CI/CD (Docker-based for Go/Rust/Python)
# =============================================================================

# Lint Go code
ci-lint-go:
	@echo "=== Linting Go (capture) ==="
	docker run --rm -v $(PWD)/packages/capture:/app -w /app golangci/golangci-lint:latest golangci-lint run

# Lint Rust code
ci-lint-rust:
	@echo "=== Linting Rust (parser) ==="
	docker run --rm -v $(PWD)/packages/parser:/app -w /app rust:1.83 cargo clippy -- -D warnings

# Lint Python code
ci-lint-python:
	@echo "=== Linting Python ==="
	docker run --rm -v $(PWD)/packages/simulator:/app -w /app ghcr.io/astral-sh/uv:python3.11-alpine uvx ruff check src/
	docker run --rm -v $(PWD)/packages/feature-engine:/app -w /app ghcr.io/astral-sh/uv:python3.11-alpine uvx ruff check src/ tests/
	docker run --rm -v $(PWD)/packages/anomaly-detection:/app -w /app ghcr.io/astral-sh/uv:python3.11-alpine uvx ruff check src/
	docker run --rm -v $(PWD)/packages/alerting:/app -w /app ghcr.io/astral-sh/uv:python3.11-alpine uvx ruff check src/

# All linting (non-JS)
ci-lint-native:
	@$(MAKE) ci-lint-go
	@$(MAKE) ci-lint-rust
	@$(MAKE) ci-lint-python

# Combined lint (use in CI after yarn lint)
ci-lint: ci-lint-native
	@echo ""
	@echo "Native linting complete. Run 'yarn lint' for JS/TS."

# Test Go code
ci-test-go:
	@echo "=== Testing Go (capture) ==="
	docker run --rm -v $(PWD)/packages/capture:/app -w /app golang:1.23 go test -v ./...

# Test Rust code
ci-test-rust:
	@echo "=== Testing Rust (parser) ==="
	docker run --rm -v $(PWD)/packages/parser:/app -w /app rust:1.83 cargo test

# Test Python code (feature-engine has tests)
ci-test-python:
	@echo "=== Testing Python ==="
	docker run --rm -v $(PWD)/packages/feature-engine:/app -w /app ghcr.io/astral-sh/uv:python3.11-alpine sh -c \
		"uv sync --dev && uv run pytest tests/ -v" || true

# All testing (non-JS)
ci-test-native:
	@$(MAKE) ci-test-go
	@$(MAKE) ci-test-rust
	@$(MAKE) ci-test-python

# Combined test (use in CI after yarn test)
ci-test: ci-test-native
	@echo ""
	@echo "Native testing complete. Run 'yarn test' for JS/TS."

# Build all Docker images
ci-build:
	docker compose build

# Full CI pipeline (native languages only - run yarn ci separately)
ci-native: ci-lint-native ci-test-native ci-build
	@echo ""
	@echo "=== Native CI Complete ==="

# Full CI (assumes yarn ci has been run)
ci: ci-native
	@echo ""
	@echo "=== Full CI Complete ==="
	@echo "Note: Run 'yarn ci' for JS/TS before this."

# =============================================================================
# Kafka Utilities
# =============================================================================

kafka-topics:
	docker compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

kafka-consume-raw:
	docker compose exec kafka kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.raw.packets \
		--from-beginning --max-messages 10

kafka-consume-parsed:
	docker compose exec kafka kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.parsed.modbus \
		--from-beginning --max-messages 10

kafka-consume-features:
	docker compose exec kafka kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.features \
		--from-beginning --max-messages 10

kafka-consume-anomalies:
	docker compose exec kafka kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.anomalies \
		--from-beginning --max-messages 10

kafka-consume-alerts:
	docker compose exec kafka kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.alerts \
		--from-beginning --max-messages 10

# =============================================================================
# Training
# =============================================================================

train:
	@echo "Training anomaly detection models from Kafka..."
	docker compose run --rm anomaly-detection python scripts/train.py \
		--kafka-brokers kafka:9092 \
		--kafka-topic ics.features \
		--output-dir /app/models \
		--max-samples 5000 \
		--epochs 30
	@echo ""
	@echo "Training complete! Models saved to anomaly_models volume."

# =============================================================================
# Integration Testing
# =============================================================================

test-integration: dev-alerting
	@echo "Waiting for services to stabilize..."
	@sleep 15
	@echo ""
	@echo "=== Running Integration Tests ==="
	@echo "Checking service health..."
	@curl -sf http://localhost:8083/health > /dev/null && echo "✓ Simulator healthy" || echo "✗ Simulator unhealthy"
	@curl -sf http://localhost:8084/health > /dev/null && echo "✓ Alerting healthy" || echo "✗ Alerting unhealthy"
	@echo ""
	@echo "Triggering attack..."
	@curl -sf -X POST http://localhost:8083/attack/start -H 'Content-Type: application/json' -d '{"mode": "reconnaissance"}' > /dev/null
	@echo "Waiting for alerts..."
	@sleep 70
	@echo ""
	@echo "Checking for alerts..."
	@curl -sf http://localhost:8084/alerts | head -c 200
	@echo ""
	@echo ""
	@echo "Stopping attack..."
	@curl -sf -X POST http://localhost:8083/attack/stop > /dev/null
	@echo "=== Integration Test Complete ==="

# E2E test - full pipeline verification (used in CI)
e2e-test:
	@echo "=== Running E2E Tests ==="
	./scripts/e2e-test.sh
