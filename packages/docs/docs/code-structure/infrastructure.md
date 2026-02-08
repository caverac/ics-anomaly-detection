# Infrastructure

The infrastructure package is a TypeScript AWS CDK application that defines the cloud resources for the ICS anomaly detection system.

## Overview

| Property | Value                          |
| -------- | ------------------------------ |
| Language | TypeScript                     |
| Location | `packages/infrastructure/`     |
| Tool     | AWS CDK v2                     |
| Purpose  | S3 bucket for ML model storage |

## What it does

1. **Creates S3 bucket** for storing trained ML models with versioning
2. **Configures lifecycle rules** for cost optimization (IA transition, version expiration)
3. **Enforces security** with encryption, SSL, and blocked public access
4. **Stores parameters** in SSM Parameter Store for service discovery
5. **Supports multiple environments** (development, staging, production)

## Package structure

```
packages/infrastructure/
├── src/
│   ├── bin/
│   │   └── index.ts              # CDK app entry point
│   └── lib/
│       ├── models.stack.ts       # S3 bucket for ML models
│       └── models.stack.spec.ts  # Unit tests
├── package.json
├── cdk.json
├── tsconfig.json
└── jest.config.js
```

## Stacks

### ModelsStack

Creates an S3 bucket for ML model storage with production-ready configuration:

| Feature               | Description                               |
| --------------------- | ----------------------------------------- |
| Versioning            | Enabled for model rollback                |
| Encryption            | S3-managed (AES-256)                      |
| Public access         | Blocked                                   |
| SSL                   | Enforced                                  |
| Lifecycle: IA         | Transition non-current versions after 30d |
| Lifecycle: Expiration | Delete non-current versions after 90d     |
| Removal policy        | RETAIN in production, DESTROY otherwise   |

**Bucket naming**: `ics-anomaly-detection-models-{environment}`

**SSM Parameters created**:

- `/ics-anomaly-detection/{env}/models/bucket-name`
- `/ics-anomaly-detection/{env}/models/bucket-arn`

## How to deploy

### Prerequisites

- AWS CLI configured with credentials
- Node.js 22+

### Commands

```bash
cd packages/infrastructure

# Install dependencies
yarn install

# Synthesize CloudFormation (preview)
ENVIRONMENT=development yarn synth

# Deploy to AWS
ENVIRONMENT=development yarn deploy

# Compare changes with deployed stack
ENVIRONMENT=development yarn diff

# Run tests
yarn test
```

### Environment variables

| Variable      | Description      | Required | Values                                 |
| ------------- | ---------------- | -------- | -------------------------------------- |
| `ENVIRONMENT` | Deployment stage | Yes      | `development`, `staging`, `production` |
| `AWS_ACCOUNT` | AWS account ID   | No       | Uses CDK default if not set            |
| `AWS_REGION`  | AWS region       | No       | Default: `us-east-1`                   |

## Integration with anomaly-detection

The anomaly-detection service can use S3 for model storage instead of local volumes:

```bash
# Configure anomaly-detection to use S3
MODEL_STORAGE_STORE_TYPE=s3
MODEL_STORAGE_S3_BUCKET=ics-anomaly-detection-models-development
MODEL_STORAGE_S3_PREFIX=models/v1.0.0/
MODEL_STORAGE_S3_REGION=us-east-1
```

### Training with S3 upload

```bash
cd packages/anomaly-detection

python scripts/train.py \
  --kafka-brokers localhost:9094 \
  --output-dir ./models \
  --upload-s3 \
  --s3-bucket ics-anomaly-detection-models-development \
  --s3-prefix models/v1.0.0/
```

## Key dependencies

| Package       | Purpose                |
| ------------- | ---------------------- |
| `aws-cdk-lib` | AWS CDK constructs     |
| `constructs`  | CDK construct base     |
| `zod`         | Environment validation |
