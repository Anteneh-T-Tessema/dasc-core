import time
from dasc.kernel import Kernel
from dasc.schemas import Intent

# --- Mock System Components ---

class MockDatabase:
    def __init__(self):
        self.records = {"USR_123": {"balance": 1000}, "USR_456": {"balance": 50}}
        self.version = "v2.0"

    def update_balance(self, user_id, amount):
        if user_id in self.records:
            self.records[user_id]["balance"] = amount
            print(f"[DB] Successfully updated {user_id} balance to ${amount}")
        else:
            print(f"[DB] ERROR: User {user_id} not found!")

# --- Scenarios ---

def run_unconstrained_demo(db):
    print("\n=== RUNNING UNCONSTRAINED SWARM (NO DASC) ===")
    print("Agent Scenario: Agent is told to update USR_456 but hallucinates the ID as USR_999.")
    
    # Simulating an agent directly calling the DB
    hallucinated_id = "USR_999"
    print(f"Agent: 'I will now update balance for {hallucinated_id} to $5000'")
    db.update_balance(hallucinated_id, 5000)
    print("Result: System accepted a request for a non-existent user (Cognitive Fault -> Committed).")

def run_dasc_protected_demo(db, kernel):
    print("\n=== RUNNING DASC-PROTECTED SWARM ===")
    print("Agent Scenario: Agent tries to update USR_456 with stale state data.")
    
    # Agent generates an intent with an old version of the record
    intent = Intent(
        intent_id="INT-DEMO-001",
        actor_agent="finance_agent",
        action_type="update_balance",
        target_artifact="USR_456",
        risk_tier=2,
        state_version_vector={"USR_456": "v1.0"} # Stale! DB is at v2.0
    )
    
    print(f"Agent: 'Submitting intent to update {intent.target_artifact}...'")
    decision = kernel.evaluate(intent)
    
    if decision.status == "COMMIT":
        db.update_balance("USR_456", 5000)
    else:
        print(f"DASC INTERCEPTION: {decision.status}")
        print(f"Reason: {decision.reason_codes}")
        print("Result: Cognitive fault caught at the boundary. System state preserved.")

if __name__ == "__main__":
    db = MockDatabase()
    # We prime the kernel with the CURRENT real version
    kernel = Kernel(current_state_versions={"USR_456": "v2.0"})
    
    run_unconstrained_demo(db)
    time.sleep(1)
    run_dasc_protected_demo(db, kernel)
