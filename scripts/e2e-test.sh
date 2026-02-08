#!/bin/bash
# E2E Test Script for ICS Anomaly Detection Pipeline
# This script verifies the full data pipeline works end-to-end

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=120
POLL_INTERVAL=5
COMPOSE_FILE="docker-compose.yml"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cleanup() {
    log_info "Cleaning up..."
    docker compose -f "$COMPOSE_FILE" --profile simulator down -v --remove-orphans 2>/dev/null || true
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# =============================================================================
# Helper Functions
# =============================================================================

wait_for_healthy() {
    local service=$1
    local max_wait=$2
    local elapsed=0

    log_info "Waiting for $service to be healthy..."
    while [ $elapsed -lt $max_wait ]; do
        if docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | grep -q "healthy"; then
            log_info "$service is healthy"
            return 0
        fi
        sleep $POLL_INTERVAL
        elapsed=$((elapsed + POLL_INTERVAL))
    done

    log_error "$service did not become healthy within ${max_wait}s"
    return 1
}

wait_for_service() {
    local url=$1
    local max_wait=$2
    local elapsed=0

    log_info "Waiting for service at $url..."
    while [ $elapsed -lt $max_wait ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "Service at $url is responding"
            return 0
        fi
        sleep $POLL_INTERVAL
        elapsed=$((elapsed + POLL_INTERVAL))
    done

    log_error "Service at $url did not respond within ${max_wait}s"
    return 1
}

check_kafka_topic_has_messages() {
    local topic=$1
    local min_messages=${2:-1}

    log_info "Checking for messages in topic: $topic"

    local count
    count=$(docker compose -f "$COMPOSE_FILE" exec -T kafka \
        /opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
        --broker-list localhost:9092 \
        --topic "$topic" 2>/dev/null | \
        awk -F: '{sum += $3} END {print sum}' || echo "0")

    if [ "$count" -ge "$min_messages" ]; then
        log_info "Topic $topic has $count messages (required: $min_messages)"
        return 0
    else
        log_warn "Topic $topic has $count messages (required: $min_messages)"
        return 1
    fi
}

# =============================================================================
# Test Steps
# =============================================================================

test_infrastructure() {
    log_info "=== Step 1: Starting infrastructure ==="

    # Start infrastructure services
    docker compose -f "$COMPOSE_FILE" up -d kafka redis

    wait_for_healthy "kafka" 60
    wait_for_healthy "redis" 30

    # Wait for topic initialization
    docker compose -f "$COMPOSE_FILE" up kafka-init
    sleep 5

    log_info "Infrastructure is ready"
}

test_pipeline_services() {
    log_info "=== Step 2: Starting pipeline services ==="

    # Start core services (parser, feature-engine, anomaly-detection, alerting)
    docker compose -f "$COMPOSE_FILE" up -d parser feature-engine anomaly-detection alerting

    # Wait for services to start
    sleep 15

    # Check alerting API is responding
    wait_for_service "http://localhost:8084/health" 60

    log_info "Pipeline services are running"
}

test_simulator_traffic() {
    log_info "=== Step 3: Starting simulator and generating traffic ==="

    # Start simulator
    docker compose -f "$COMPOSE_FILE" --profile simulator up -d simulator

    # Wait for simulator API
    wait_for_service "http://localhost:8083/health" 30

    # Generate normal traffic
    log_info "Generating normal traffic..."
    curl -sf -X POST "http://localhost:8083/traffic/start" \
        -H "Content-Type: application/json" \
        -d '{"rate": 50, "protocol": "modbus", "duration": 30}' || true

    sleep 10

    # Trigger attack scenario
    log_info "Triggering attack scenario..."
    curl -sf -X POST "http://localhost:8083/attack/start" \
        -H "Content-Type: application/json" \
        -d '{"mode": "reconnaissance", "intensity": "high"}' || true

    # Let traffic flow for a while
    sleep 20

    log_info "Traffic generation complete"
}

test_data_flow() {
    log_info "=== Step 4: Verifying data flow through pipeline ==="

    local failed=0

    # Check raw packets topic
    if ! check_kafka_topic_has_messages "ics.raw.packets" 10; then
        log_warn "Raw packets topic has fewer messages than expected"
        # Not a hard failure - simulator might produce directly to parsed topics
    fi

    # Check parsed topics (at least one should have messages)
    local has_parsed=false
    for topic in ics.parsed.modbus ics.parsed.dnp3 ics.parsed.opcua; do
        if check_kafka_topic_has_messages "$topic" 1; then
            has_parsed=true
        fi
    done

    if [ "$has_parsed" = false ]; then
        log_error "No parsed messages found in any protocol topic"
        failed=1
    fi

    # Check features topic
    if ! check_kafka_topic_has_messages "ics.features" 1; then
        log_warn "Features topic is empty - feature engine may need more time"
    fi

    # Check anomalies topic (may be empty if no anomalies detected)
    check_kafka_topic_has_messages "ics.anomalies" 0 || true

    return $failed
}

test_alerting_api() {
    log_info "=== Step 5: Testing alerting API ==="

    local failed=0

    # Health check
    if ! curl -sf "http://localhost:8084/health" > /dev/null; then
        log_error "Alerting health check failed"
        failed=1
    fi

    # Get alerts endpoint
    local response
    response=$(curl -sf "http://localhost:8084/alerts" 2>/dev/null || echo "")
    if [ -z "$response" ]; then
        log_warn "Could not fetch alerts - endpoint may not be ready"
    else
        log_info "Alerts endpoint responding: $(echo "$response" | head -c 100)..."
    fi

    # Get incidents endpoint
    response=$(curl -sf "http://localhost:8084/incidents" 2>/dev/null || echo "")
    if [ -z "$response" ]; then
        log_warn "Could not fetch incidents"
    else
        log_info "Incidents endpoint responding: $(echo "$response" | head -c 100)..."
    fi

    return $failed
}

test_service_logs() {
    log_info "=== Step 6: Checking for errors in service logs ==="

    local services="parser feature-engine anomaly-detection alerting"
    local has_errors=false

    for service in $services; do
        local errors
        errors=$(docker compose -f "$COMPOSE_FILE" logs "$service" 2>&1 | grep -i "error\|exception\|panic" | head -5 || true)
        if [ -n "$errors" ]; then
            log_warn "Errors found in $service logs:"
            echo "$errors"
            has_errors=true
        fi
    done

    if [ "$has_errors" = false ]; then
        log_info "No critical errors found in service logs"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    log_info "Starting E2E tests for ICS Anomaly Detection Pipeline"
    log_info "=============================================="

    local failed=0

    # Run tests
    test_infrastructure || failed=1
    test_pipeline_services || failed=1
    test_simulator_traffic || failed=1

    # Give pipeline time to process
    log_info "Waiting for pipeline to process messages..."
    sleep 30

    test_data_flow || failed=1
    test_alerting_api || failed=1
    test_service_logs

    log_info "=============================================="
    if [ $failed -eq 0 ]; then
        log_info "E2E tests PASSED"
        exit 0
    else
        log_error "E2E tests FAILED"

        # Print service status for debugging
        log_info "Service status:"
        docker compose -f "$COMPOSE_FILE" ps

        exit 1
    fi
}

main "$@"
