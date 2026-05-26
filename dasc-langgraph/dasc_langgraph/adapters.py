from typing import Dict, Any, Union
import uuid
from dasc import Kernel, Intent, Decision

class DASCLangGraphAdapter:
    """
    LangGraph Python Adapter
    Provides a safety gatekeeper node and routing edges for LangGraph workflows.
    """
    def __init__(self, kernel: Kernel):
        self.kernel = kernel

    def safety_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        The Safety Guard Node.
        Evaluates the proposed intent in the graph state against the DASC safety kernel.
        """
        proposed = state.get("proposed_intent")
        if not proposed:
            return {"error": "No intent proposed for evaluation."}

        # Handle Dict input vs Intent model input
        if isinstance(proposed, dict):
            # Auto-generate intent_id if not present
            if "intent_id" not in proposed:
                proposed["intent_id"] = f"INT-LG-{uuid.uuid4().hex[:8].upper()}"
            
            # Make sure actor_agent has a default
            if "actor_agent" not in proposed:
                proposed["actor_agent"] = "langgraph-agent"
                
            # Make sure target_artifact has a default
            if "target_artifact" not in proposed:
                proposed["target_artifact"] = "unknown_target"
                
            # Make sure action_type has a default
            if "action_type" not in proposed:
                proposed["action_type"] = "unknown_action"

            try:
                intent = Intent(**proposed)
            except Exception as e:
                return {"error": f"Invalid proposed_intent structure: {str(e)}"}
        elif isinstance(proposed, Intent):
            intent = proposed
        else:
            return {"error": "Invalid proposed_intent format. Must be dict or Intent."}

        decision = self.kernel.evaluate(intent)

        return {
            "last_decision": decision
        }

    def route_decision(self, state: Dict[str, Any]) -> str:
        """
        Conditional Edge Routing function.
        Routes the graph execution based on DASC decision status.
        """
        decision = state.get("last_decision")
        if not decision:
            return "rejected"

        if isinstance(decision, dict):
            status = decision.get("status")
        elif isinstance(decision, Decision):
            status = decision.status
        else:
            return "rejected"

        if status == "COMMIT":
            return "authorized"
        elif status == "ESCALATE":
            return "human_gate"
        else:
            return "rejected"
