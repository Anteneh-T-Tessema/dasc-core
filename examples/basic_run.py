from dasc.schemas import Intent, Evidence
from dasc.kernel import Kernel

# The "real" state of the world right now
system_state = {"payments/batch_settlement.py": "v2.0"}

# Initialize DASC
dasc_kernel = Kernel(current_state_versions=system_state)

print("--- Scenario 1: Agent submits a stale intent (OCC Failure) ---")
# The agent hallucinated or read an old version of the file
bad_intent = Intent(
    intent_id="INT-001",
    actor_agent="coder_agent",
    action_type="modify_code",
    target_artifact="payments/batch_settlement.py",
    risk_tier=2,
    state_version_vector={"payments/batch_settlement.py": "v1.0"} # Stale!
)

decision1 = dasc_kernel.evaluate(bad_intent)
print(f"Result: {decision1.status} -> {decision1.reason_codes}\n")


print("--- Scenario 2: Agent submits a valid intent ---")
good_intent = Intent(
    intent_id="INT-002",
    actor_agent="coder_agent",
    action_type="modify_code",
    target_artifact="payments/batch_settlement.py",
    risk_tier=3,
    state_version_vector={"payments/batch_settlement.py": "v2.0"}, # Matches!
    compensation_plan={"revert_intent": "revert_patch_002"}       # Safe!
)

decision2 = dasc_kernel.evaluate(good_intent)
print(f"Result: {decision2.status}\n")
