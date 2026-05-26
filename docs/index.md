# Deterministic Agentic Swarm Control (DASC)

**Governing Probabilistic Intelligence in High-Stakes Systems.**

DASC is an open-source middleware designed to intercept outputs from AI orchestration frameworks and enforce deterministic safety checks before actions are committed.

## Why DASC?

In modern AI orchestration, failures fall into two categories:

1.  **Cognitive Faults**: Probabilistic reasoning errors (hallucinations, logic gaps).
2.  **Committed Faults**: Unauthorized or unsafe state changes in the authoritative world.

DASC introduces a **Commitment Boundary** that ensures cognitive faults never become committed faults.

## Language Support

DASC provides native, protocol-compatible implementations for both major AI ecosystems:

### Python (dasc-core)
```bash
pip install dasc-core
```

### Node.js / TypeScript (dasc-node)
```bash
npm install dasc-node
```

## Core Features

*   **Semantic OCC**: Hash-based content verification for optimistic concurrency control.
*   **Typed Intent Protocol**: Strict schema-based API contracts for all agent actions.
*   **Bitemporal Ledger**: Tamper-evident, hash-chained audit trails.
*   **Policy Registry**: Pluggable safety rules for Cybersecurity, Finance, and Healthcare.
*   **Human-in-the-Loop**: Built-in escalation paths for high-risk autonomous decisions.

## Framework Integrations

DASC integrates seamlessly with your existing agent stack:
- **Python**: LangGraph, CrewAI, AutoGen.
- **Node.js**: LangChain.js, LangGraph.js, CrewAI-JS.

## Learn More

*   [Visual Architecture](ARCHITECTURE.md)
*   [API Documentation](api.md)
*   [Read the Research Paper](DASC_Academic_Paper.md)
