import os
import logging
from dasc.kernel import Kernel
from dasc.schemas import Intent
from dasc.exceptions import OCCConflictError, EscalationRequired
from dasc.utils import calculate_file_hash

# 1. Setup a dummy file for hashing demo
dummy_file = "production_test.txt"
with open(dummy_file, "w") as f:
    f.write("Initial Content v1.0")

# 2. Calculate its current hash
initial_hash = calculate_file_hash(dummy_file)
print(f"File Hash: {initial_hash}")

# 3. Initialize Kernel
kernel = Kernel()

print("\n--- Testing Structured Logging & Hash-based OCC ---")
good_intent = Intent(
    intent_id="PROD-001",
    actor_agent="ops_agent",
    action_type="update_file",
    target_artifact=dummy_file,
    state_version_vector={dummy_file: f"hash:{initial_hash}"}
)

# This should commit successfully (will see DASC log messages)
kernel.evaluate(good_intent)

print("\n--- Testing Exception Handling (Forcing OCC Conflict) ---")
# Modify file externally
with open(dummy_file, "w") as f:
    f.write("Content has been changed by someone else!")

try:
    kernel.evaluate(good_intent, raise_on_failure=True)
except OCCConflictError as e:
    print(f"Caught Expected Exception: {type(e).__name__} for intent {e.intent_id}")

print("\n--- Testing Tier 4 Escalation ---")
critical_intent = Intent(
    intent_id="PROD-002",
    actor_agent="admin_agent",
    action_type="shutdown_server",
    target_artifact="core_cluster",
    risk_tier=4,
    compensation_plan={"reboot": "restore_state"}
)

try:
    kernel.evaluate(critical_intent, raise_on_failure=True)
except EscalationRequired:
    print("System identified Tier 4 action and triggered Escalation path.")

# Cleanup
if os.path.exists(dummy_file):
    os.remove(dummy_file)
