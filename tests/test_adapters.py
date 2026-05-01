import pytest
from dasc.kernel import Kernel
from dasc.schemas import Intent
from dasc.adapters.langchain import DASCCommitTool
from dasc.adapters.autogen import DASCGatekeeper

def test_langchain_tool_adapter():
    kernel = Kernel()
    tool = DASCCommitTool(kernel=kernel)
    
    # Simulate a LangChain call
    result = tool._run(
        intent_id="LC-001",
        actor_agent="test_agent",
        action_type="write_file",
        target_artifact="test.txt",
        risk_tier=1
    )
    
    assert "COMMIT_SUCCESS" in result
    assert "LC-001" in result

def test_autogen_gatekeeper_adapter():
    kernel = Kernel()
    gatekeeper = DASCGatekeeper(kernel=kernel)
    
    # Mock executor that just returns success
    def mock_executor(args): return "SUCCESS"
    
    wrapped = gatekeeper.wrap_executor(mock_executor)
    
    # Test rejection (missing metadata)
    res = wrapped({})
    assert "REJECTED" in res
    
    # Test valid flow
    intent_dict = {
        "intent_id": "AG-001",
        "actor_agent": "agent",
        "action_type": "read",
        "target_artifact": "file",
        "risk_tier": 1
    }
    res = wrapped({"dasc_intent": intent_dict})
    assert res == "SUCCESS"

def test_adapter_escalation_logic():
    kernel = Kernel()
    tool = DASCCommitTool(kernel=kernel)
    
    # Tier 4 should trigger ESCALATE (if compensation plan is provided)
    result = tool._run(
        intent_id="LC-002",
        actor_agent="admin",
        action_type="delete_user",
        target_artifact="USR_123",
        risk_tier=4,
        compensation_plan={"action": "restore"}
    )
    
    assert "REJECTED" in result # In the tool, we treat non-COMMIT as REJECTED for the agent
    assert "TIER_4_MANDATORY_ESCALATION" in result
