# DASC Architecture

This document describes the high-level architecture and deterministic logic flow of the Deterministic Agentic Swarm Control (DASC) middleware.

## System Overview

DASC acts as a **Commitment Boundary** between a probabilistic multi-agent swarm and the authoritative system state.

```mermaid
graph TD
    subgraph "Probabilistic Swarm (LLMs)"
        A[Agent A] -->|Generate| I[Typed Intent]
        B[Agent B] -->|Generate| I
    end

    subgraph "DASC Commitment Boundary"
        I --> K[DASC Kernel]
        K -->|Evaluate| P[Policy Engine]
        K -->|Verify| O[OCC / Hashing]
        K -->|Inspect| T[Taint / IFC]
    end

    subgraph "Authoritative State"
        K -->|COMMIT| S[(System State)]
        K -->|REJECT| R[Error Handling]
        K -->|ESCALATE| H[Human-in-the-Loop]
    end

    K -->|Log| L[(Bitemporal Ledger)]
```

## Intent Evaluation Pipeline

Every intent passes through a linear, deterministic pipeline. If any stage fails, the process halts immediately with a `REJECT` status.

```mermaid
sequenceDiagram
    participant A as Agent Swarm
    participant K as DASC Kernel
    participant L as Bitemporal Ledger
    participant S as System State

    A->>K: Submit TypedIntent
    Note over K: 1. Schema Validation
    alt Invalid Schema
        K->>A: REJECT (Schema Error)
    else Valid Schema
        Note over K: 2. IFC / Taint Check
        Note over K: 3. OCC / Version Check
        Note over K: 4. Policy / Risk Check
        
        alt All Checks Pass
            K->>L: Record COMMIT
            K->>S: Authorize Execution
            K->>A: Return COMMIT
        else Check Failed
            K->>L: Record REJECT
            K->>A: Return REJECT (Reason)
        end
    end
```

## Bitemporal Ledger Schema

DASC maintains a SQLite-backed ledger that records not just what happened, but **what was known** at the time of the decision.

| Field | Description |
| :--- | :--- |
| `intent_id` | Unique identifier for the action proposal. |
| `actor_agent` | The specific agent that generated the intent. |
| `status` | COMMIT, REJECT, or ESCALATE. |
| `reason_codes` | Deterministic reasons for the decision. |
| `intent_json` | Full snapshot of the original intent for replayability. |
| `timestamp` | UTC ISO-8601 timestamp of the decision. |
