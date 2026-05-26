# DASC-Core Node.js SDK

**Deterministic Agentic Safety Controller (DASC) for TypeScript & Node.js.**

`@antenehtessema/dasc-core` is the official TypeScript implementation of the DASC safety middleware. It provides a deterministic commitment boundary for AI agents, ensuring that cognitive hallucinations never become committed system faults.

## 🚀 Quick Start

```bash
npm install @antenehtessema/dasc-core
```

### Basic Usage

```typescript
import { Kernel } from '@antenehtessema/dasc-core';

const kernel = new Kernel();

const intent = {
  intent_id: "task-001",
  actor_agent: "researcher",
  action_type: "FILE_WRITE",
  risk_tier: 2,
  evidence: [{ source_type: "trusted" }],
  payload: { path: "report.md", content: "..." }
};

const decision = kernel.evaluate(intent);

if (decision.status === 'COMMIT') {
  console.log("Action Authorized!");
} else {
  console.error("Action Rejected:", decision.reason_codes);
}
```

## 🖥 CLI

DASC-Core includes a professional CLI for ledger inspection:

```bash
# Inspect the audit trail
npx dasc-core inspect --limit 20

# Generate a hash for Semantic OCC
npx dasc-core hash config.json
```

## 📄 License

MIT © 2026 Anteneh T. Tessema
