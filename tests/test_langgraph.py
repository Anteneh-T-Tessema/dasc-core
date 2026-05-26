import sys
import os
# Ensure dasc-langgraph is in the Python import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../dasc-langgraph")))

import pytest
from dasc.kernel import Kernel
from dasc.schemas import Intent
from dasc_langgraph import DASCLangGraphAdapter

def test_langgraph_safety_node_commit():
    kernel = Kernel()
    adapter = DASCLangGraphAdapter(kernel)
    
    state = {
        "proposed_intent": {
            "intent_id": "LG-T1",
            "actor_agent": "graph-agent",
            "action_type": "write",
            "target_artifact": "file.txt",
            "risk_tier": 1
        }
    }
    
    result = adapter.safety_node(state)
    assert "last_decision" in result
    assert result["last_decision"].status == "COMMIT"
    
    # Test routing
    state["last_decision"] = result["last_decision"]
    route = adapter.route_decision(state)
    assert route == "authorized"

def test_langgraph_safety_node_reject():
    kernel = Kernel()
    adapter = DASCLangGraphAdapter(kernel)
    
    # Tier 3 without compensation plan is rejected
    state = {
        "proposed_intent": {
            "intent_id": "LG-T2",
            "actor_agent": "graph-agent",
            "action_type": "delete",
            "target_artifact": "db",
            "risk_tier": 3
        }
    }
    
    result = adapter.safety_node(state)
    assert "last_decision" in result
    assert result["last_decision"].status == "REJECT"
    
    state["last_decision"] = result["last_decision"]
    route = adapter.route_decision(state)
    assert route == "rejected"

def test_langgraph_safety_node_escalate():
    kernel = Kernel()
    adapter = DASCLangGraphAdapter(kernel)
    
    # Tier 4 triggers escalate
    state = {
        "proposed_intent": {
            "intent_id": "LG-T3",
            "actor_agent": "graph-agent",
            "action_type": "delete_all",
            "target_artifact": "db",
            "risk_tier": 4,
            "compensation_plan": {"undo": "restore"}
        }
    }
    
    result = adapter.safety_node(state)
    assert "last_decision" in result
    assert result["last_decision"].status == "ESCALATE"
    
    state["last_decision"] = result["last_decision"]
    route = adapter.route_decision(state)
    assert route == "human_gate"

def test_langgraph_safety_node_invalid_intent():
    kernel = Kernel()
    adapter = DASCLangGraphAdapter(kernel)
    
    state = {}
    result = adapter.safety_node(state)
    assert "error" in result
    assert "No intent proposed" in result["error"]

def test_langgraph_checkpointer(tmp_path):
    from dasc_langgraph import DASCLangGraphCheckpointer
    
    db_file = tmp_path / "test_langgraph_checkpoint.db"
    checkpointer = DASCLangGraphCheckpointer(db_path=str(db_file))
    
    config = {"configurable": {"thread_id": "thread-1"}}
    checkpoint = {
        "id": "chk-1",
        "ts": "2026-05-26T10:00:00Z",
        "v": 1,
        "channel_values": {"my_key": "my_val"}
    }
    metadata = {"source": "test"}
    
    # 1. Put checkpoint
    res = checkpointer.put(config, checkpoint, metadata)
    assert res["configurable"]["checkpoint_id"] == "chk-1"
    
    # 2. Get checkpoint tuple
    tup = checkpointer.get_tuple(config)
    assert tup is not None
    assert tup.checkpoint["id"] == "chk-1"
    assert tup.checkpoint["channel_values"]["my_key"] == "my_val"
    assert tup.metadata["source"] == "test"
