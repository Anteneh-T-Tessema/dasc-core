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
- **Optimistic Concurrency Control (OCC)**: Prevents TOCTOU (Time-of-Check to Time-of-Use) vulnerabilities.
- **SQLite Ledger**: Persistent, bitemporal audit log of every decision.

## Quick Start

```python
from dasc.kernel import Kernel
from dasc.adapters.langchain import DASCCommitTool

kernel = Kernel()
dasc_tool = DASCCommitTool(kernel=kernel)

# Add dasc_tool to your LangChain agent's toolset
```

## Documentation

The theoretical foundation of DASC is detailed in the accompanying research paper:
- **Research Paper (PDF)**: [docs/DASC_Academic_Paper.pdf](docs/DASC_Academic_Paper.pdf)
- **Technical Overview**: [docs/DASC_Academic_Paper.md](docs/DASC_Academic_Paper.md)

## Examples

Run the comparative demo to see DASC in action:
```bash
python -m examples.demo_scenario
```

## License

MIT
