// Package main provides the entry point for the ICS packet capture service.
// It captures network packets from specified interfaces and publishes them to Kafka.
package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/caverac/ics-anomaly-detection/packages/capture/internal/capture"
	"github.com/caverac/ics-anomaly-detection/packages/capture/internal/config"
	"github.com/caverac/ics-anomaly-detection/packages/capture/internal/kafka"
	"github.com/caverac/ics-anomaly-detection/packages/capture/pkg/types"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

func main() {
	// Parse command line flags
	configPath := flag.String("config", "", "Path to configuration file")
	flag.Parse()

	// Load configuration
	cfg, err := config.Load(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load config: %v\n", err)
		os.Exit(1)
	}

	// Initialize logger
	logger, err := initLogger(cfg.Logging)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer func() { _ = logger.Sync() }()

	logger.Info("starting ICS capture service",
		zap.String("interface", cfg.Capture.Interface),
		zap.Strings("kafka_brokers", cfg.Kafka.Brokers),
	)

	// Create context with cancellation
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Initialize Kafka producer
	producer, err := kafka.NewProducer(cfg.Kafka, logger)
	if err != nil {
		logger.Fatal("failed to create kafka producer", zap.Error(err))
	}
	defer func() { _ = producer.Close() }()

	// Initialize capturer
	capturer := capture.New(cfg.Capture, logger)
	if err := capturer.Open(); err != nil {
		logger.Fatal("failed to open capture handle", zap.Error(err))
	}
	defer capturer.Close()

	// Start metrics server
	go startMetricsServer(logger, capturer)

	// Start packet processing goroutine
	go processPackets(ctx, logger, capturer, producer)

	// Start capture in main goroutine
	go func() {
		if err := capturer.Run(ctx); err != nil && ctx.Err() == nil {
			logger.Error("capture error", zap.Error(err))
			cancel()
		}
	}()

	// Wait for shutdown signal
	sig := <-sigChan
	logger.Info("received shutdown signal", zap.String("signal", sig.String()))

	// Graceful shutdown
	cancel()

	// Give time for cleanup
	time.Sleep(time.Second)

	// Log final stats
	stats := capturer.Stats()
	logger.Info("capture statistics",
		zap.Uint64("packets_captured", stats.PacketsCaptured),
		zap.Uint64("packets_published", stats.PacketsPublished),
		zap.Uint64("packets_dropped", stats.PacketsDropped),
		zap.Uint64("bytes_captured", stats.BytesCaptured),
		zap.Uint64("errors", stats.ErrorCount),
	)
}

func initLogger(cfg config.LoggingConfig) (*zap.Logger, error) {
	var zapCfg zap.Config

	if cfg.Format == "console" {
		zapCfg = zap.NewDevelopmentConfig()
	} else {
		zapCfg = zap.NewProductionConfig()
	}

	// Parse log level
	level, err := zapcore.ParseLevel(cfg.Level)
	if err != nil {
		level = zapcore.InfoLevel
	}
	zapCfg.Level = zap.NewAtomicLevelAt(level)

	return zapCfg.Build()
}

func processPackets(ctx context.Context, logger *zap.Logger, capturer *capture.Capturer, producer *kafka.Producer) {
	batch := make([]*types.RawPacket, 0, 100)
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	flushBatch := func() {
		if len(batch) == 0 {
			return
		}

		if err := producer.PublishBatch(ctx, batch); err != nil {
			logger.Error("failed to publish batch", zap.Error(err), zap.Int("batch_size", len(batch)))
		}
		batch = batch[:0]
	}

	for {
		select {
		case <-ctx.Done():
			flushBatch()
			return

		case <-ticker.C:
			flushBatch()

		case packet, ok := <-capturer.Packets():
			if !ok {
				flushBatch()
				return
			}

			batch = append(batch, packet)

			if len(batch) >= 100 {
				flushBatch()
			}
		}
	}
}

func startMetricsServer(logger *zap.Logger, capturer *capture.Capturer) {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"healthy"}`))
	})

	mux.HandleFunc("/metrics", func(w http.ResponseWriter, _ *http.Request) {
		stats := capturer.Stats()
		w.Header().Set("Content-Type", "text/plain")
		_, _ = fmt.Fprintf(w, "# HELP capture_packets_total Total packets captured\n")
		_, _ = fmt.Fprintf(w, "# TYPE capture_packets_total counter\n")
		_, _ = fmt.Fprintf(w, "capture_packets_total %d\n", stats.PacketsCaptured)
		_, _ = fmt.Fprintf(w, "# HELP capture_packets_published_total Total packets published to Kafka\n")
		_, _ = fmt.Fprintf(w, "# TYPE capture_packets_published_total counter\n")
		_, _ = fmt.Fprintf(w, "capture_packets_published_total %d\n", stats.PacketsPublished)
		_, _ = fmt.Fprintf(w, "# HELP capture_packets_dropped_total Total packets dropped due to buffer full\n")
		_, _ = fmt.Fprintf(w, "# TYPE capture_packets_dropped_total counter\n")
		_, _ = fmt.Fprintf(w, "capture_packets_dropped_total %d\n", stats.PacketsDropped)
		_, _ = fmt.Fprintf(w, "# HELP capture_bytes_total Total bytes captured\n")
		_, _ = fmt.Fprintf(w, "# TYPE capture_bytes_total counter\n")
		_, _ = fmt.Fprintf(w, "capture_bytes_total %d\n", stats.BytesCaptured)
		_, _ = fmt.Fprintf(w, "# HELP capture_errors_total Total capture errors\n")
		_, _ = fmt.Fprintf(w, "# TYPE capture_errors_total counter\n")
		_, _ = fmt.Fprintf(w, "capture_errors_total %d\n", stats.ErrorCount)
	})

	server := &http.Server{
		Addr:              ":8081",
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
	}

	logger.Info("starting metrics server", zap.String("addr", ":8081"))
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Error("metrics server error", zap.Error(err))
	}
}
