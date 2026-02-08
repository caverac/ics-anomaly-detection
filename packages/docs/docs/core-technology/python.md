# Python

Python is used for **ML/data-intensive services**: feature-engine, anomaly-detection, alerting, and simulator.

## Why Python?

### ML ecosystem dominance
Python has the richest ML ecosystem:
- **PyTorch/TensorFlow** for deep learning
- **scikit-learn** for classical ML
- **NumPy/Pandas** for data manipulation
- Pre-trained models and research implementations

No other language comes close for ML workloads.

### Rapid prototyping
ML development is iterative. Python's dynamic typing and REPL enable fast experimentation:
- Try different feature combinations
- Test model architectures
- Visualize results in Jupyter

### Excellent async support
`asyncio` and `confluent-kafka` work well together for:
- Non-blocking Kafka consumption
- Concurrent HTTP APIs (FastAPI)
- Background processing tasks

### FastAPI for APIs
FastAPI provides:
- Automatic OpenAPI documentation
- Pydantic validation
- Async request handling
- Type hints for better tooling

### Data science integration
Jupyter notebooks allow interactive exploration:
- Feature importance analysis
- Model evaluation
- Anomaly investigation

## Alternatives considered

| Alternative | Pros | Cons |
|-------------|------|------|
| **Java (DL4J, Spark MLlib)** | JVM performance, enterprise support | Smaller ML ecosystem, verbose |
| **Scala (Spark)** | Distributed processing | Overkill for single-node, complex |
| **Go (GoLearn)** | Performance | Immature ML ecosystem |
| **Rust (linfa)** | Performance, safety | Very limited ML libraries |
| **Julia** | Scientific computing focus | Smaller ecosystem, less production tooling |

## Limitations

### GIL (Global Interpreter Lock)
Python's GIL prevents true parallelism in CPU-bound code. Mitigations:
- Use NumPy/PyTorch (release GIL in C extensions)
- Use multiprocessing for CPU parallelism
- Async I/O for I/O-bound work

### Runtime performance
Python is slower than compiled languages. For this project:
- Hot paths use NumPy/PyTorch (C/C++ under the hood)
- Kafka I/O dominates latency, not Python
- Feature extraction at 1000s of msg/sec is achievable

### Dependency management complexity
Python packaging has historically been messy. We use:
- **uv** for fast, reliable package installation
- **pyproject.toml** for modern configuration
- Docker for reproducible environments

### Type safety
Python's dynamic typing can hide bugs. Mitigations:
- **Pydantic** for runtime validation
- **Type hints** throughout
- **mypy** for static analysis

### Memory usage
Python's memory overhead is higher than compiled languages. For ML workloads, model tensors dominate memory anyway.

## Usage in this project

| Package | Purpose |
|---------|---------|
| `feature-engine` | Time-window feature extraction |
| `anomaly-detection` | ML model inference (Isolation Forest, LSTM, SVM) |
| `alerting` | Alert correlation, deduplication, notifications |
| `simulator` | Synthetic traffic generation |

## Key dependencies

| Package | Purpose |
|---------|---------|
| `confluent-kafka` | Kafka consumer/producer |
| `fastapi` | REST API framework |
| `pydantic` | Data validation |
| `torch` | Deep learning (LSTM autoencoder) |
| `scikit-learn` | Classical ML (Isolation Forest, SVM) |
| `numpy` | Numerical computing |
| `structlog` | Structured logging |
| `redis` | State storage (alerting) |

## Python version

The project uses **Python 3.12+** for:
- Performance improvements
- Better error messages
- Type hint improvements
- `match` statement support
