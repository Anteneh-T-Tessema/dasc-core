# Contributing to DASC-Core

First off, thank you for considering contributing to DASC! It's people like you that make DASC such a great tool for the AI community.

## 🌈 Our Mission
To provide a deterministic commitment boundary for all agentic systems, ensuring safety and auditability by default.

## 🚀 How Can I Contribute?

### 1. Proposing a New Safety Policy
We are always looking for new industry-specific policies (e.g., Legal, Supply Chain, Retail).
- Policies should be deterministic (no LLM-based logic inside the kernel).
- Create your policy in `src/policies/<industry>.ts`.

### 2. Adding a Framework Adapter
If you use an agent framework not yet supported (e.g., PydanticAI, BabyAGI), we'd love an adapter!
- Adapters should provide a way to intercept "intents" before they are executed.
- Add your adapter to `src/adapters/<framework>.ts`.

## 🛠 Development Workflow

### Python Package & Core Middleware
1. Install development dependencies:
   ```bash
   pip install -e .
   pip install pytest
   ```
2. Run the test suite:
   ```bash
   pytest
   ```

### Node.js SDK & adapters
1. Install dependencies:
   ```bash
   cd dasc-node && npm install
   ```
2. Run TypeScript/Vitest tests:
   ```bash
   npm test
   ```

### Dashboard Frontend & Control Plane
1. Development environment:
   ```bash
   cd dashboard && npm install
   npm run dev
   ```
2. **Bundle Dashboard for Python (`pip`) Release**:
   If you make any changes to the Next.js frontend dashboard, you must rebuild the static assets and bundle them into the `dasc` Python package so that they are served by the FastAPI `dasc serve` command:
   ```bash
   cd dashboard
   npm run build:py
   ```
   This will compile Next.js to a static export and automatically copy all static files into `dasc/dashboard/`.

## 🛡 Security
Please refer to our [Security Policy](SECURITY.md) for reporting vulnerabilities.

## 📜 License
By contributing, you agree that your contributions will be licensed under its MIT License.
