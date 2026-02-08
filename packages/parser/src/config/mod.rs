use anyhow::Result;
use config::{Config, Environment, File};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Settings {
    pub kafka: KafkaSettings,
    #[serde(default = "default_metrics_port")]
    pub metrics_port: u16,
}

fn default_metrics_port() -> u16 {
    8082
}

#[derive(Debug, Deserialize)]
pub struct KafkaSettings {
    pub brokers: String,
    pub group_id: String,
    pub input_topic: String,
    pub client_id: String,
    pub auto_offset_reset: String,
}

impl Settings {
    pub fn new() -> Result<Self> {
        let config = Config::builder()
            // Default values
            .set_default("kafka.brokers", "localhost:9092")?
            .set_default("kafka.group_id", "ics-parser")?
            .set_default("kafka.input_topic", "ics.raw.packets")?
            .set_default("kafka.client_id", "ics-parser")?
            .set_default("kafka.auto_offset_reset", "earliest")?
            .set_default("metrics_port", 8082_i64)?
            // Load from config file if exists
            .add_source(File::with_name("config").required(false))
            // Override with environment variables (KAFKA_BROKERS, etc.)
            .add_source(Environment::default().separator("_").try_parsing(true))
            .build()?;

        Ok(config.try_deserialize()?)
    }
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            kafka: KafkaSettings {
                brokers: "localhost:9092".to_string(),
                group_id: "ics-parser".to_string(),
                input_topic: "ics.raw.packets".to_string(),
                client_id: "ics-parser".to_string(),
                auto_offset_reset: "earliest".to_string(),
            },
            metrics_port: 8082,
        }
    }
}
