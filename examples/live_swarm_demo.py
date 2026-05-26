import sys
import os
import time

# Ensure packages are in the import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../dasc-langgraph")))

from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from dasc import DASCClient
from dasc_langgraph import DASCLangGraphAdapter

# 1. Define LangGraph State
class AgentState(TypedDict):
    proposed_intent: Dict[str, Any]
    last_decision: Any
    executed_action: str
    error: str

# 2. Define standard graph nodes
def execute_action(state: AgentState) -> Dict[str, Any]:
    print(f"\n[SYSTEM] AUTHORIZED: Executing action '{state['proposed_intent']['action_type']}' on '{state['proposed_intent']['target_artifact']}'...")
    return {"executed_action": "SUCCESS"}

def handle_rejection(state: AgentState) -> Dict[str, Any]:
    reasons = state["last_decision"].reason_codes
    suggestions = state["last_decision"].suggestions
    print(f"\n[SYSTEM] REJECTED: Safety violation! Reasons: {reasons}. Suggestions: {suggestions}")
    return {"executed_action": "REJECTED"}

def human_escalation_gate(state: AgentState) -> Dict[str, Any]:
    intent_id = state["proposed_intent"]["intent_id"]
    print(f"\n[DASC] ⚠️ ESCALATED: Intent '{intent_id}' requires manual human approval.")
    print(">>> Action: Please open the DASC Control Plane Dashboard (http://localhost:3000)")
    print(f">>> Find Intent '{intent_id}' and click either 'Approve' or 'Deny'.")
    print(">>> The demo will resume once you perform the action on the dashboard.")
    
    # Wait for the user to make a decision on the dashboard
    client = DASCClient()
    while True:
        try:
            history = client.get_ledger()
            # Find the latest decision recorded for this intent
            records = [r for r in history if r["intent_id"] == intent_id]
            # Since SQLite logs approvals as new decisions, let's find if any is COMMIT or REJECT
            committed = [r for r in records if r["status"] in ["COMMIT", "REJECT"]]
            if committed:
                final_status = committed[0]["status"]
                print(f"\n[DASC] Received human approval status: {final_status}!")
                # Update last decision in state
                state["last_decision"].status = final_status
                return {"last_decision": state["last_decision"]}
        except Exception as e:
            print(f"Polling error: {str(e)}")
        
        time.sleep(2)

# 3. Main execution loop
if __name__ == "__main__":
    print("=" * 80)
    print(" DASC LIVE AGENT SWARM DEMO ")
    print("=" * 80)

    # Connect to DASC Control Plane
    client = DASCClient()
    adapter = DASCLangGraphAdapter(client)

    # Build LangGraph workflow
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("safety_gate", adapter.safety_node)
    workflow.add_node("execute", execute_action)
    workflow.add_node("reject", handle_rejection)
    workflow.add_node("escalate", human_escalation_gate)
    
    # Define routing conditional edges
    workflow.add_conditional_edges(
        "safety_gate",
        adapter.route_decision,
        {
            "authorized": "execute",
            "rejected": "reject",
            "human_gate": "escalate"
        }
    )
    
    # Define next steps after human decision is captured in the escalate node
    workflow.add_conditional_edges(
        "escalate",
        adapter.route_decision,
        {
            "authorized": "execute",
            "rejected": "reject"
        }
    )
    
    workflow.set_entry_point("safety_gate")
    workflow.add_edge("execute", END)
    workflow.add_edge("reject", END)
    
    app = workflow.compile()

    # --- Scenario 1: Safe Intent ---
    print("\n--- Running Scenario 1: Safe Action (Tier 1) ---")
    safe_intent = {
        "intent_id": "LG-SAFE-1",
        "actor_agent": "reader-agent",
        "action_type": "READ_FILE",
        "target_artifact": "public_data.csv",
        "risk_tier": 1
    }
    app.invoke({"proposed_intent": safe_intent})
    time.sleep(2)

    # --- Scenario 2: Stale Intent (OCC Violation) ---
    print("\n--- Running Scenario 2: Stale Action (OCC Conflict) ---")
    # Tell DASC server about the target version baseline (FastAPI server state starts empty, so "v2.0" will conflict with "v1.0")
    stale_intent = {
        "intent_id": "LG-STALE-2",
        "actor_agent": "writer-agent",
        "action_type": "UPDATE_CONFIG",
        "target_artifact": "payments/batch_settlement.py",
        "state_version_vector": {"payments/batch_settlement.py": "v1.0"}, # Proposed stale version
        "risk_tier": 1
    }
    
    # First, let's register the current database state version as 'v2.0' in the kernel.
    # For this demo, we simulate version mismatches by submitting stale version vectors.
    # Note: DASC server's mock database state versions default to {"config.json": "v1.0.0"} or similar.
    # In kernel.py: if current_v exists and current_v != version, it triggers OCC conflict.
    # Let's target "config.json" with version "v0.9.0" (current server version is "v1.0.0").
    stale_intent["target_artifact"] = "config.json"
    stale_intent["state_version_vector"] = {"config.json": "v0.9.0"} # Server expects v1.0.0
    
    app.invoke({"proposed_intent": stale_intent})
    time.sleep(2)

    # --- Scenario 3: Destructive Action (Tier 4 Escalation) ---
    print("\n--- Running Scenario 3: Destructive Action (Tier 4 - HITL Escalation) ---")
    destructive_intent = {
        "intent_id": "LG-HITL-3",
        "actor_agent": "admin-agent",
        "action_type": "DELETE_USER_RECORDS",
        "target_artifact": "USR_992",
        "risk_tier": 4, # Mandatory escalation
        "compensation_plan": {"undo": "restore_user"},
        "payload": {"provenance_id": "EHR-992-DEV"}
    }
    app.invoke({"proposed_intent": destructive_intent})
    
    print("\nDemo Completed Successfully!")
