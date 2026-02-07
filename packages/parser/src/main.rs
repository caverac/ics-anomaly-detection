mod config;
mod kafka;
mod protocols;

use anyhow::Result;
use std::sync::Arc;
use tokio::signal;
use tokio::sync::broadcast;
use tracing::{error, info};

use crate::config::Settings;
use crate::kafka::{Consumer, Producer};
use crate::protocols::Parser;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("ics_parser=debug".parse()?)
                .add_directive("rdkafka=warn".parse()?),
        )
        .json()
        .init();

    info!("Starting ICS Protocol Parser");

    // Load configuration
    let settings = Settings::new()?;
    info!(?settings, "Configuration loaded");

    // Create shutdown channel
    let (shutdown_tx, _) = broadcast::channel::<()>(1);

    // Initialize parser
    let parser = Arc::new(Parser::new());

    // Initialize Kafka consumer
    let consumer = Consumer::new(&settings.kafka)?;

    // Initialize Kafka producer
    let producer = Arc::new(Producer::new(&settings.kafka)?);

    // Start metrics server
    let metrics_handle = tokio::spawn(start_metrics_server(settings.metrics_port));

    // Start processing
    let shutdown_rx = shutdown_tx.subscribe();
    let processing_handle = tokio::spawn(process_messages(
        consumer,
        producer,
        parser,
        shutdown_rx,
    ));

    // Wait for shutdown signal
    shutdown_signal().await;
    info!("Shutdown signal received");

    // Signal shutdown to workers
    let _ = shutdown_tx.send(());

    // Wait for processing to complete
    let _ = tokio::time::timeout(
        std::time::Duration::from_secs(10),
        processing_handle,
    )
    .await;

    metrics_handle.abort();

    info!("ICS Parser shutdown complete");
    Ok(())
}

async fn process_messages(
    consumer: Consumer,
    producer: Arc<Producer>,
    parser: Arc<Parser>,
    mut shutdown: broadcast::Receiver<()>,
) -> Result<()> {
    info!("Starting message processing");

    loop {
        tokio::select! {
            _ = shutdown.recv() => {
                info!("Processing shutdown requested");
                break;
            }
            result = consumer.recv() => {
                match result {
                    Ok(msg) => {
                        if let Err(e) = handle_message(&msg, &parser, &producer).await {
                            error!(?e, "Failed to process message");
                        }
                    }
                    Err(e) => {
                        error!(?e, "Failed to receive message");
                    }
                }
            }
        }
    }

    Ok(())
}

async fn handle_message(
    msg: &kafka::RawPacketMessage,
    parser: &Parser,
    producer: &Producer,
) -> Result<()> {
    // Decode hex payload
    let payload = hex::decode(&msg.payload_hex)?;

    // Parse based on ICS protocol
    let parsed = match msg.ics_protocol.as_str() {
        "modbus" => parser.parse_modbus(&payload, msg),
        "dnp3" => parser.parse_dnp3(&payload, msg),
        "opcua" => parser.parse_opcua(&payload, msg),
        _ => {
            tracing::debug!(protocol = %msg.ics_protocol, "Unknown protocol, skipping");
            return Ok(());
        }
    };

    match parsed {
        Ok(parsed_msg) => {
            let topic = format!("ics.parsed.{}", msg.ics_protocol);
            producer.send(&topic, &parsed_msg).await?;
        }
        Err(e) => {
            tracing::warn!(?e, protocol = %msg.ics_protocol, "Failed to parse message");
        }
    }

    Ok(())
}

async fn start_metrics_server(port: u16) {
    use axum::{routing::get, Router};

    let app = Router::new()
        .route("/health", get(|| async { "OK" }))
        .route("/metrics", get(metrics_handler));

    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{}", port))
        .await
        .expect("Failed to bind metrics server");

    info!(port, "Metrics server started");

    axum::serve(listener, app).await.expect("Metrics server failed");
}

async fn metrics_handler() -> String {
    use prometheus::Encoder;
    let encoder = prometheus::TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer).unwrap();
    String::from_utf8(buffer).unwrap()
}

async fn shutdown_signal() {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("Failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }
}
