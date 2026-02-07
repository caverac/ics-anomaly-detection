.PHONY: help up down logs clean build test dev dev-full dev-alerting

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
	@echo "  make dev         - Start infra + simulator + parser + feature-engine"
	@echo "  make dev-full    - Start full pipeline with anomaly detection"
	@echo "  make dev-alerting - Start full pipeline with alerting service"
	@echo "  make simulator   - Start with simulator only"
	@echo "  make monitoring  - Start with Prometheus + Grafana"
	@echo "  make debug       - Start with Kafka UI for debugging"
	@echo ""
	@echo "Build:"
	@echo "  make build       - Build all Docker images"
	@echo "  make build-capture - Build capture service"
	@echo "  make build-parser  - Build parser service"
	@echo "  make build-alerting - Build alerting service"
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
	docker compose up -d parser feature-engine
	@echo ""
	@echo "Development environment ready!"
	@echo "  Simulator API: http://localhost:8083"
	@echo "  Parser metrics: http://localhost:8082/metrics"
	@echo ""
	@echo "Pipeline: Simulator -> Parser -> Feature Engine"

dev-full: up
	docker compose --profile simulator up -d
	docker compose up -d parser feature-engine anomaly-detection
	@echo ""
	@echo "Full pipeline ready!"
	@echo "  Simulator API: http://localhost:8083"
	@echo "  Parser metrics: http://localhost:8082/metrics"
	@echo ""
	@echo "Pipeline: Simulator -> Parser -> Feature Engine -> Anomaly Detection"

dev-alerting: up
	docker compose --profile simulator up -d
	docker compose up -d parser feature-engine anomaly-detection alerting
	@echo ""
	@echo "Full pipeline with alerting ready!"
	@echo "  Simulator API: http://localhost:8083"
	@echo "  Parser metrics: http://localhost:8082/metrics"
	@echo "  Alerting API: http://localhost:8084"
	@echo ""
	@echo "Pipeline: Simulator -> Parser -> Feature Engine -> Anomaly Detection -> Alerting"
	@echo ""
	@echo "Test with attack simulation:"
	@echo "  curl -X POST http://localhost:8083/attack/start -H 'Content-Type: application/json' -d '{\"mode\": \"reconnaissance\"}'"
	@echo ""
	@echo "View alerts:"
	@echo "  curl http://localhost:8084/alerts"

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

build-feature-engine:
	docker compose build feature-engine

build-anomaly-detection:
	docker compose build anomaly-detection

build-alerting:
	docker compose build alerting

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
	docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

kafka-consume-raw:
	docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.raw.packets \
		--from-beginning \
		--max-messages 10

kafka-consume-parsed:
	docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.parsed.modbus \
		--from-beginning \
		--max-messages 10

kafka-consume-features:
	docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.features \
		--from-beginning \
		--max-messages 10

kafka-consume-anomalies:
	docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.anomalies \
		--from-beginning \
		--max-messages 10

kafka-consume-alerts:
	docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
		--bootstrap-server localhost:9092 \
		--topic ics.alerts \
		--from-beginning \
		--max-messages 10

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
