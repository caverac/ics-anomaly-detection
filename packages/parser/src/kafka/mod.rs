use anyhow::{Context, Result};
use rdkafka::config::ClientConfig;
use rdkafka::consumer::{Consumer as KafkaConsumer, StreamConsumer};
use rdkafka::producer::{FutureProducer, FutureRecord};
use rdkafka::Message;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tracing::{debug, info};

use crate::config::KafkaSettings;

/// Raw packet message from the capture service
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct RawPacketMessage {
    pub timestamp: String,
    pub src_ip: String,
    pub dst_ip: String,
    pub src_port: u16,
    pub dst_port: u16,
    pub protocol: String,
    pub ics_protocol: String,
    pub payload_size: usize,
    pub payload_hex: String,
}

/// Kafka consumer for raw packets
pub struct Consumer {
    consumer: StreamConsumer,
}

impl Consumer {
    pub fn new(settings: &KafkaSettings) -> Result<Self> {
        let consumer: StreamConsumer = ClientConfig::new()
            .set("bootstrap.servers", &settings.brokers)
            .set("group.id", &settings.group_id)
            .set("client.id", &settings.client_id)
            .set("auto.offset.reset", &settings.auto_offset_reset)
            .set("enable.auto.commit", "true")
            .set("auto.commit.interval.ms", "1000")
            .set("session.timeout.ms", "30000")
            .create()
            .context("Failed to create Kafka consumer")?;

        consumer
            .subscribe(&[&settings.input_topic])
            .context("Failed to subscribe to topic")?;

        info!(topic = %settings.input_topic, "Subscribed to Kafka topic");

        Ok(Self { consumer })
    }

    pub async fn recv(&self) -> Result<RawPacketMessage> {
        let message = self
            .consumer
            .recv()
            .await
            .context("Failed to receive message")?;

        let payload = message
            .payload()
            .context("Empty message payload")?;

        let msg: RawPacketMessage = serde_json::from_slice(payload)
            .context("Failed to deserialize message")?;

        debug!(
            src = %msg.src_ip,
            dst = %msg.dst_ip,
            protocol = %msg.ics_protocol,
            "Received raw packet"
        );

        Ok(msg)
    }
}

/// Kafka producer for parsed messages
pub struct Producer {
    producer: FutureProducer,
}

impl Producer {
    pub fn new(settings: &KafkaSettings) -> Result<Self> {
        let producer: FutureProducer = ClientConfig::new()
            .set("bootstrap.servers", &settings.brokers)
            .set("client.id", format!("{}-producer", settings.client_id))
            .set("message.timeout.ms", "5000")
            .set("compression.type", "gzip")
            .set("batch.size", "16384")
            .set("linger.ms", "5")
            .create()
            .context("Failed to create Kafka producer")?;

        info!("Kafka producer created");

        Ok(Self { producer })
    }

    pub async fn send<T: Serialize>(&self, topic: &str, message: &T) -> Result<()> {
        let payload = serde_json::to_string(message)?;

        let record = FutureRecord::to(topic)
            .payload(&payload)
            .key("");

        self.producer
            .send(record, Duration::from_secs(5))
            .await
            .map_err(|(e, _)| anyhow::anyhow!("Failed to send message: {:?}", e))?;

        debug!(topic, "Message sent to Kafka");

        Ok(())
    }

    #[allow(dead_code)]
    pub async fn send_with_key<T: Serialize>(
        &self,
        topic: &str,
        key: &str,
        message: &T,
    ) -> Result<()> {
        let payload = serde_json::to_string(message)?;

        let record = FutureRecord::to(topic)
            .payload(&payload)
            .key(key);

        self.producer
            .send(record, Duration::from_secs(5))
            .await
            .map_err(|(e, _)| anyhow::anyhow!("Failed to send message: {:?}", e))?;

        Ok(())
    }
}
