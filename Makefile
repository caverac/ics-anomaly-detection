.PHONY: help up down logs clean build test dev

# Default target
help:
	@echo "ICS Anomaly Detection - Development Commands"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make up          - Start core infrastructure (Kafka, Redis)"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - Tail all logs"
	@echo "  make clean       - Remove all containers and volumes"
	@echo ""
	@echo "Development:"
	@echo "  make dev         - Start infra + simulator + parser"
	@echo "  make simulator   - Start with simulator only"
	@echo "  make monitoring  - Start with Prometheus + Grafana"
	@echo "  make debug       - Start with Kafka UI for debugging"
	@echo ""
	@echo "Build:"
	@echo "  make build       - Build all Docker images"
	@echo "  make build-capture - Build capture service"
	@echo "  make build-parser  - Build parser service"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs        - Start documentation site"

# =============================================================================
# Infrastructure
# =============================================================================

up:
	docker compose up -d kafka redis
	@echo "Waiting for Kafka to be ready..."
	@sleep 10
	docker compose up -d kafka-init
	@echo ""
	@echo "Infrastructure is ready!"
	@echo "  Kafka: localhost:9094"
	@echo "  Redis: localhost:6379"

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# =============================================================================
# Development Modes
# =============================================================================

dev: up
	docker compose --profile simulator up -d
	docker compose up -d parser
	@echo ""
	@echo "Development environment ready!"
	@echo "  Simulator API: http://localhost:8083"
	@echo "  Parser metrics: http://localhost:8082/metrics"

simulator: up
	docker compose --profile simulator up -d
	@echo ""
	@echo "Simulator started!"
	@echo "  API: http://localhost:8083"
	@echo "  Status: curl http://localhost:8083/status"

monitoring: up
	docker compose --profile monitoring up -d
	@echo ""
	@echo "Monitoring started!"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3001 (admin/admin)"

debug: up
	docker compose --profile debug up -d
	@echo ""
	@echo "Debug tools started!"
	@echo "  Kafka UI: http://localhost:8080"

# =============================================================================
# Build
# =============================================================================

build:
	docker compose build

build-capture:
	docker compose build capture

build-parser:
	docker compose build parser

build-simulator:
	docker compose build simulator

# =============================================================================
# Documentation
# =============================================================================

docs:
	cd packages/docs && yarn start

docs-build:
	cd packages/docs && yarn build

# =============================================================================
# Testing
# =============================================================================

test:
	@echo "Running tests..."
	cd packages/capture && go test ./... || true
	cd packages/parser && cargo test || true

# =============================================================================
# Kafka Tools
# =============================================================================

kafka-topics:
	docker compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

kafka-consume-raw:
	docker compose exec kafka kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.raw.packets \
		--from-beginning \
		--max-messages 10

kafka-consume-parsed:
	docker compose exec kafka kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.parsed.modbus \
		--from-beginning \
		--max-messages 10
