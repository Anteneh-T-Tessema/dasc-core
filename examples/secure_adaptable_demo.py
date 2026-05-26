import os
from dasc.kernel import Kernel
from dasc.decorators import dasc_gate
from dasc.exceptions import PolicyViolationError

# 1. Initialize Secure Kernel
if os.path.exists("dasc_ledger.db"):
    os.remove("dasc_ledger.db")

kernel = Kernel()

# 2. Add a Custom Policy (Adaptability)
def budget_policy(intent):
    """Rejects actions from 'intern_agent' if risk tier > 1"""
    if intent.actor_agent == "intern_agent" and intent.risk_tier > 1:
        return False, "Interns cannot perform high-risk actions"
    return True, ""

kernel.register_policy(budget_policy)

# 3. Use the Decorator (Ease of Use)
@dasc_gate(kernel, risk_tier=2)
def sensitive_operation(api_key):
    print(f"Executing sensitive operation with key: {api_key}")

print("--- Testing Custom Policy ---")
from dasc.schemas import Intent
intern_intent = Intent(
    intent_id="SEC-001",
    actor_agent="intern_agent",
    action_type="delete_db",
    target_artifact="production",
    risk_tier=2
)
try:
    kernel.evaluate(intern_intent, raise_on_failure=True)
except Exception as e:
    print(f"Caught: {str(e)}")

print("\n--- Testing Credential Scrubbing ---")
# The API key should be scrubbed from the ledger automatically
try:
    sensitive_operation(api_key="sk-live-1234567890abcdef1234567890")
except Exception:
    pass

# Verify scrubbing in ledger
history = kernel.ledger.get_history()
last_intent_json = history[0]["intent_json"]
if "sk-live" not in last_intent_json:
    print("Security Success: API key was scrubbed from the ledger JSON.")
else:
    print("Security Failure: API key leaked into the ledger!")

print("\n--- Testing Hash-Chain Integrity ---")
is_intact = kernel.ledger.verify_integrity()
print(f"Ledger Integrity Intact: {is_intact}")

# Simulate Tampering
print("\n--- Simulating Database Tampering ---")
import sqlite3
with sqlite3.connect("dasc_ledger.db") as conn:
    conn.execute("UPDATE decisions SET status='COMMIT' WHERE status='REJECT'")

is_intact_after_tamper = kernel.ledger.verify_integrity()
print(f"Ledger Integrity Intact after tampering: {is_intact_after_tamper}")
if not is_intact_after_tamper:
    print("Result: DASC detected unauthorized ledger modification!")

# Cleanup
if os.path.exists("dasc_ledger.db"):
    os.remove("dasc_ledger.db")
