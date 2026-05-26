# DASC-LangGraph

LangGraph orchestration adapter for the DASC deterministic safety middleware.

## Installation

```bash
pip install dasc-langgraph
```

## Usage

```python
from langgraph.graph import StateGraph, END
from typing import Dict, Any, TypedDict
from dasc import Kernel
from dasc_langgraph import DASCLangGraphAdapter

# 1. Define graph state
class AgentState(TypedDict):
    proposed_intent: Dict[str, Any]
    last_decision: Any
    # your other state keys...

# 2. Initialize DASC Kernel and LangGraph Adapter
kernel = Kernel()
adapter = DASCLangGraphAdapter(kernel)

# 3. Build graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("safety_gate", adapter.safety_node)
workflow.add_node("execute_action", execute_action_node)
workflow.add_node("request_approval", human_approval_node)
workflow.add_node("handle_rejection", rejection_handler_node)

# Set entry point
workflow.set_entry_point("safety_gate")

# Add conditional routing
workflow.add_conditional_edges(
    "safety_gate",
    adapter.route_decision,
    {
        "authorized": "execute_action",
        "human_gate": "request_approval",
        "rejected": "handle_rejection"
    }
)

# Compile graph
app = workflow.compile()
```
