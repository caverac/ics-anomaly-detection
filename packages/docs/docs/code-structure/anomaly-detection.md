# Anomaly Detection

The anomaly detection service is a Python application that consumes feature vectors and classifies them using an ensemble of ML models.

## Overview

| Property | Value                         |
| -------- | ----------------------------- |
| Language | Python                        |
| Location | `packages/anomaly-detection/` |
| Input    | Kafka topic `ics.features`    |
| Output   | Kafka topic `ics.anomalies`   |

## What it does

1. **Consumes feature vectors** from the feature engine
2. **Runs inference** through multiple models (Isolation Forest, One-Class SVM, LSTM Autoencoder)
3. **Combines scores** using weighted ensemble voting
4. **Classifies results** as normal, suspicious, anomaly, or critical
5. **Identifies anomaly types** (reconnaissance, timing anomaly, protocol violation, etc.)
6. **Publishes anomaly results** for the alerting service

## Package structure

```
packages/anomaly-detection/
├── src/
│   ├── main.py                    # Entry point, AnomalyDetector class
│   ├── config.py                  # Pydantic settings
│   ├── kafka/
│   │   ├── consumer.py            # Feature vector consumer
│   │   └── producer.py            # Anomaly result producer
│   ├── schemas/
│   │   └── anomaly.py             # AnomalyResult, Classification, AnomalyType
│   ├── models/
│   │   ├── base.py                # Base model interface
│   │   ├── ensemble.py            # EnsembleModel combining all models
│   │   ├── isolation_forest.py    # Isolation Forest implementation
│   │   ├── one_class_svm.py       # One-Class SVM implementation
│   │   └── lstm_autoencoder.py    # LSTM Autoencoder for sequences
│   ├── inference/
│   │   ├── engine.py              # InferenceEngine orchestrator
│   │   ├── classifier.py          # Anomaly type classification
│   │   └── hot_reload.py          # Model hot-reloading support
│   ├── preprocessing/
│   │   └── normalizer.py          # Feature normalization
│   └── training/
│       └── trainer.py             # Model training utilities
├── models/                        # Trained model files (.joblib, .pt)
├── tests/
├── requirements.txt
└── Dockerfile
```

## ML models

### Isolation Forest

Statistical anomaly detection that isolates anomalies by randomly partitioning features. Good for detecting point anomalies in high-dimensional data.

### One-Class SVM

Support vector machine trained only on normal data. Creates a boundary around normal behavior and flags outliers.

### LSTM Autoencoder

Neural network that learns to reconstruct normal traffic sequences. High reconstruction error indicates anomalies. Captures temporal patterns.

### Ensemble

Combines model scores using configurable weights:

- Each model produces a score from 0.0 (normal) to 1.0 (anomaly)
- Weighted average determines final score
- Thresholds map scores to classifications

## Classification levels

| Level        | Score Range | Description                         |
| ------------ | ----------- | ----------------------------------- |
| `NORMAL`     | 0.0 - 0.3   | Expected behavior                   |
| `SUSPICIOUS` | 0.3 - 0.5   | Slightly unusual, worth monitoring  |
| `ANOMALY`    | 0.5 - 0.8   | Significant deviation from baseline |
| `CRITICAL`   | 0.8 - 1.0   | Severe anomaly, likely attack       |

## Anomaly types

| Type                  | Description                       |
| --------------------- | --------------------------------- |
| `RECONNAISSANCE`      | Network scanning, enumeration     |
| `TIMING_ANOMALY`      | Unusual request timing patterns   |
| `VOLUME_ANOMALY`      | Abnormal traffic volume           |
| `PROTOCOL_VIOLATION`  | Invalid or unusual protocol usage |
| `UNAUTHORIZED_ACCESS` | Access to restricted addresses    |
| `DATA_EXFILTRATION`   | Large data transfers              |
| `COMMAND_INJECTION`   | Unexpected write operations       |

## Output schema

```json
{
  "window_key": {
    "src_ip": "192.168.1.100",
    "dst_ip": "192.168.1.10",
    "protocol": "modbus",
    "window_size": 60,
    "window_start": 1704067200
  },
  "detected_at": "2024-01-15T10:30:05.123456Z",
  "model_scores": [
    {
      "model_name": "isolation_forest",
      "score": 0.75,
      "weight": 0.4,
      "raw_score": -0.3,
      "inference_time_ms": 0.5
    },
    {
      "model_name": "one_class_svm",
      "score": 0.68,
      "weight": 0.3,
      "raw_score": -0.2,
      "inference_time_ms": 0.3
    },
    {
      "model_name": "lstm_autoencoder",
      "score": 0.82,
      "weight": 0.3,
      "raw_score": 0.15,
      "inference_time_ms": 2.1
    }
  ],
  "ensemble_score": 0.75,
  "classification": "anomaly",
  "anomaly_type": "reconnaissance",
  "confidence": 0.85,
  "feature_contributions": {
    "fc_unique_count": 0.25,
    "addr_range": 0.2,
    "fc_entropy": 0.15
  }
}
```

## Configuration

| Environment Variable          | Description            | Default          |
| ----------------------------- | ---------------------- | ---------------- |
| `KAFKA_BOOTSTRAP_SERVERS`     | Kafka broker addresses | `localhost:9092` |
| `KAFKA_INPUT_TOPIC`           | Input topic            | `ics.features`   |
| `KAFKA_OUTPUT_TOPIC`          | Output topic           | `ics.anomalies`  |
| `MODEL_PATH`                  | Path to trained models | `./models`       |
| `MODEL_HOT_RELOAD`            | Enable hot-reloading   | `true`           |
| `ANOMALY_DETECTION_LOG_LEVEL` | Log level              | `INFO`           |

## How to run

### With Docker Compose

```bash
# Start the full pipeline
make dev-full

# View logs
docker compose logs -f anomaly-detection
```

### Local development

```bash
cd packages/anomaly-detection

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python -m src.main

# Run tests
pytest tests/ -v
```

## Key dependencies

| Package           | Purpose                         |
| ----------------- | ------------------------------- |
| `confluent-kafka` | Kafka consumer/producer         |
| `scikit-learn`    | Isolation Forest, One-Class SVM |
| `torch`           | LSTM Autoencoder                |
| `numpy`           | Numerical computations          |
| `pydantic`        | Data validation                 |
| `structlog`       | Structured logging              |
