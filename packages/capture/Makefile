.PHONY: build run test clean deps fmt lint test-coverage test-coverage-html check

BINARY_NAME=capture
BUILD_DIR=bin

# Go parameters
GOCMD=go
GOBUILD=$(GOCMD) build
GORUN=$(GOCMD) run
GOTEST=$(GOCMD) test
GOGET=$(GOCMD) get
GOMOD=$(GOCMD) mod
GOFMT=gofmt

# Build flags
LDFLAGS=-ldflags "-s -w"

all: deps build

deps:
	$(GOMOD) download
	$(GOMOD) tidy

build:
	mkdir -p $(BUILD_DIR)
	CGO_ENABLED=1 $(GOBUILD) $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/capture

run:
	$(GORUN) ./cmd/capture -config config.yaml

# Run with sudo (required for packet capture)
run-sudo:
	sudo $(GOBUILD) -o $(BUILD_DIR)/$(BINARY_NAME) ./cmd/capture
	sudo $(BUILD_DIR)/$(BINARY_NAME) -config config.yaml

test:
	$(GOTEST) -v ./...

test-coverage:
	$(GOTEST) -coverprofile=coverage.out ./...
	@echo "\n=== Coverage Summary ==="
	@$(GOCMD) tool cover -func=coverage.out | grep total | awk '{print "Total Coverage: " $$3}'

test-coverage-html: test-coverage
	$(GOCMD) tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report generated: coverage.html"

# Run all checks (lint + test + coverage)
check: lint test-coverage
	@echo "\n=== All checks passed ==="

clean:
	rm -rf $(BUILD_DIR)
	rm -f coverage.out coverage.html

fmt:
	$(GOFMT) -s -w .

lint:
	golangci-lint run

# Docker build
docker-build:
	docker build -t ics-capture:latest .

# Install libpcap on different platforms
install-deps-macos:
	brew install libpcap

install-deps-ubuntu:
	sudo apt-get update && sudo apt-get install -y libpcap-dev

install-deps-alpine:
	apk add --no-cache libpcap-dev gcc musl-dev
