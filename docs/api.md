# API Reference

Detailed documentation for the `dasc-core` classes and methods.

## `dasc.kernel.Kernel`

The primary engine for evaluating intents and enforcing safety policies.

### `.evaluate(intent, raise_on_failure=False)`
Evaluates a `TypedIntent` against all deterministic checks and custom policies.

*   **Parameters**:
    *   `intent` (Intent): The intent to evaluate.
    *   `raise_on_failure` (bool): If True, raises a specific DASC error on rejection or escalation.
*   **Returns**: `Decision` object.

### `.register_policy(policy_func)`
Registers a custom safety policy.

*   **Parameters**:
    *   `policy_func` (Callable): A function taking an `Intent` and returning `(bool, str)`.

## `dasc.ledger.BitemporalLedger`

A tamper-evident, hash-chained SQLite ledger for auditability.

### `.verify_integrity()`
Verifies the cryptographic hash-chain of the entire ledger. Returns `True` if intact.

## `dasc.decorators.dasc_gate`

A high-level decorator for protecting Python functions.

### Usage
```python
@dasc_gate(kernel, risk_tier=2)
def my_function(args):
    ...
```
