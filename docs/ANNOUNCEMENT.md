# Show HN: DASC-Core – A Deterministic Safety Boundary for AI Agent Swarms

Hi everyone,

I’m excited to share **DASC (Deterministic Agentic Safety Controller)**, an open-source middleware designed to prevent AI hallucinations from becoming real-world disasters.

### The Problem
AI Agents are probabilistic. They hallucinate, they make logic errors, and they can be manipulated. In an enterprise setting, a "cognitive fault" (the LLM making a mistake) shouldn't automatically become a "committed fault" (the system executing a dangerous command).

### The Solution: DASC
DASC acts as a hard commitment boundary. It intercepts "Intents" from any framework (LangGraph, CrewAI, AutoGen) and runs them through a linear, deterministic pipeline:
1. **Schema Validation**: Is the intent well-formed?
2. **IFC / Taint Check**: Is the evidence from an untrusted source?
3. **Semantic OCC**: Is the agent acting on a stale version of the world?
4. **Deterministic Policy Engine**: Does it violate industry-specific rules (e.g., spending limits, restricted paths)?

### Features
- **Multi-Language Support**: Native implementations in **Python** and **Node.js (TypeScript)**.
- **Bitemporal Ledger**: Every decision is recorded in a hash-chained SQLite ledger for full auditability.
- **Human-in-the-Loop**: Automatic escalation to a Control Plane for high-risk actions.
- **Zero-Dependency Core**: The safety logic is deterministic and reproducible.

### Why this matters?
As we move from "Chatbots" to "Agentic Swarms," the risk of unconstrained execution grows exponentially. DASC provides the guardrails needed to deploy agents in sensitive industries like Finance, Healthcare, and Cybersecurity.

**GitHub**: [https://github.com/Anteneh-T-Tessema/dasc-core](https://github.com/Anteneh-T-Tessema/dasc-core)

I'd love to hear your thoughts on how we can make agentic workflows safer!
