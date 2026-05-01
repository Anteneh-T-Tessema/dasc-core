# DASC: Deterministic Agentic Swarm Control

## The Cognitive Fault vs. Committed Fault Paradigm

In modern AI orchestration, failures generally fall into two categories:

1.  **Cognitive Faults**: The LLM makes a mistake in reasoning, hallucinates a value, or misinterprets a state.
2.  **Committed Faults**: The system allows a cognitive fault to be executed against the authoritative state of the world.

### The Commitment Boundary
DASC introduces a "Commitment Boundary" that separates the probabilistic reasoning layer (where cognitive faults are expected) from the deterministic execution layer. By requiring every action to be presented as a **Typed Intent** with associated **Evidence**, DASC ensures that cognitive faults are caught before they become committed faults.

## Architecture
- **Probabilistic Swarm**: Generates intents.
- **DASC Kernel**: Intercepts and validates intents.
- **Authoritative State**: Only updated if the Kernel issues a `COMMIT`.

## Safety Mechanisms
- **Optimistic Concurrency Control (OCC)**: Prevents race conditions and TOCTOU errors.
- **Bitemporal Ledger**: Records every decision for audit and replay.
- **Risk-Based Gating**: Escalates high-risk actions to human oversight.
