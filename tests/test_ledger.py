import os
import pytest
from dasc.ledger import BitemporalLedger
from dasc.schemas import Intent, Decision

def test_ledger_persistence(tmp_path):
    db_file = tmp_path / "test_ledger.db"
    ledger = BitemporalLedger(db_path=str(db_file))
    
    intent = Intent(
        intent_id="L1",
        actor_agent="test_agent",
        action_type="test",
        target_artifact="test_art",
        risk_tier=1
    )
    decision = Decision(intent_id="L1", status="COMMIT")
    
    ledger.log_decision(intent, decision)
    
    # Re-initialize ledger from same file
    ledger2 = BitemporalLedger(db_path=str(db_file))
    history = ledger2.get_history()
    
    assert len(history) == 1
    assert history[0]["intent_id"] == "L1"
    assert history[0]["status"] == "COMMIT"
