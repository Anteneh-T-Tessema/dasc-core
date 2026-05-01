# DASC-Core

DASC (Deterministic Agentic Safety Controller) is an open-source middleware designed to intercept outputs from AI orchestration frameworks (like LangGraph, AutoGen, and CrewAI) and enforce deterministic safety checks before actions are committed.

## The Paradigm: Cognitive Fault vs. Committed Fault

DASC operates on the principle that AI agents *will* fail. These are **Cognitive Faults** (hallucinations, logic errors). Our goal is to prevent these from becoming **Committed Faults** (actual state changes). DASC provides the deterministic boundary where these faults are intercepted.

## Installation

```bash
pip install dasc-core
```

## Features

- **LangChain/LangGraph Integration**: Use `DASCCommitTool` to wrap agent actions.
- **AutoGen Support**: Use `DASCGatekeeper` to intercept and validate function calls.
- **Semantic OCC (Hashing)**: Use `hash:<sha256>` in version vectors for automatic file content verification.
- **Structured Observability**: Built-in logging with detailed evaluation stages.
- **Programmable Rejections**: Custom exceptions (`OCCConflictError`, etc.) for robust error handling.
- **Bitemporal SQLite Ledger**: Persistent audit log of every decision.

## Quick Start

### Using the Kernel with Exceptions

```python
from dasc.kernel import Kernel
from dasc.exceptions import OCCConflictError

kernel = Kernel()

try:
    kernel.evaluate(intent, raise_on_failure=True)
except OCCConflictError:
    # Trigger agent retry or state refresh logic
    pass
```

### Using Semantic OCC (Hashing)

```python
from dasc.utils import calculate_file_hash

file_hash = calculate_file_hash("data.json")
intent = Intent(
    ...,
    state_version_vector={"data.json": f"hash:{file_hash}"}
)
```

## Documentation

The theoretical foundation of DASC is detailed in the accompanying research paper:
- **Research Paper (PDF)**: [docs/DASC_Academic_Paper.pdf](docs/DASC_Academic_Paper.pdf)
- **Technical Overview**: [docs/DASC_Academic_Paper.md](docs/DASC_Academic_Paper.md)

## Examples

Run the production features demo:
```bash
python -m examples.production_features
```

## License

MIT
