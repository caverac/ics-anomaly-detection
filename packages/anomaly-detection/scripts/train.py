#!/usr/bin/env python3
"""CLI entry point for training anomaly detection models."""

import argparse
import logging
import sys
from pathlib import Path

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(handler)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Train anomaly detection models for ICS traffic",
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("/app/data"),
        help="Directory containing training data files",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/app/models"),
        help="Directory to save trained models",
    )

    parser.add_argument(
        "--kafka-brokers",
        type=str,
        default=None,
        help="Kafka bootstrap servers (e.g., kafka:9092)",
    )

    parser.add_argument(
        "--kafka-topic",
        type=str,
        default="ics.features",
        help="Kafka topic to load features from",
    )

    parser.add_argument(
        "--max-samples",
        type=int,
        default=10000,
        help="Maximum samples to load from Kafka",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs for LSTM",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for LSTM training",
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
        help="Learning rate for LSTM training",
    )

    parser.add_argument(
        "--validation-split",
        type=float,
        default=0.2,
        help="Fraction of data to use for validation",
    )

    parser.add_argument(
        "--mlflow-uri",
        type=str,
        default="http://localhost:5000",
        help="MLflow tracking server URI",
    )

    # S3 upload options
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Upload trained models to S3 after training",
    )

    parser.add_argument(
        "--s3-bucket",
        type=str,
        default=None,
        help="S3 bucket for model upload (required if --upload-s3)",
    )

    parser.add_argument(
        "--s3-prefix",
        type=str,
        default="models/latest/",
        help="S3 key prefix for models (e.g., 'models/v1.0.0/')",
    )

    parser.add_argument(
        "--s3-region",
        type=str,
        default="us-east-1",
        help="AWS region for S3",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Validate S3 args
    if args.upload_s3 and not args.s3_bucket:
        parser.error("--s3-bucket is required when using --upload-s3")

    configure_logging(args.log_level)
    logger = structlog.get_logger()

    logger.info(
        "training_starting",
        data_dir=str(args.data_dir),
        output_dir=str(args.output_dir),
        kafka_brokers=args.kafka_brokers,
    )

    try:
        # Verify torch is available before starting
        try:
            import torch

            logger.info("torch_available", version=torch.__version__)
        except ImportError as e:
            logger.error("torch_not_available", error=str(e))
            logger.error(
                "install_torch",
                hint="pip install torch --index-url https://download.pytorch.org/whl/cpu",
            )
            return 1

        from src.config import KafkaSettings, TrainingSettings
        from src.training.pipeline import TrainingPipeline

        training_settings = TrainingSettings(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            validation_split=args.validation_split,
            mlflow_tracking_uri=args.mlflow_uri,
        )

        kafka_settings = None
        if args.kafka_brokers:
            kafka_settings = KafkaSettings(
                bootstrap_servers=args.kafka_brokers,
                input_topic=args.kafka_topic,
            )

        pipeline = TrainingPipeline(training_settings)
        ensemble = pipeline.train(
            kafka_settings=kafka_settings,
            max_samples=args.max_samples,
        )

        logger.info(
            "training_complete",
            models=list(m.name for m in ensemble.models),
            output_dir=str(args.output_dir),
        )

        # Upload to S3 if requested
        if args.upload_s3:
            logger.info(
                "uploading_models_to_s3",
                bucket=args.s3_bucket,
                prefix=args.s3_prefix,
            )
            from src.storage.s3 import S3ModelStore

            s3_store = S3ModelStore(
                bucket=args.s3_bucket,
                prefix=args.s3_prefix,
                region=args.s3_region,
            )
            s3_store.upload_models(args.output_dir)
            logger.info(
                "models_uploaded_to_s3",
                bucket=args.s3_bucket,
                prefix=args.s3_prefix,
            )

        return 0

    except KeyboardInterrupt:
        logger.info("training_interrupted")
        return 130

    except Exception as e:
        logger.error("training_failed", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
