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

def test_ledger_time_travel(tmp_path):
    db_file = tmp_path / "test_ledger_time_travel.db"
    ledger = BitemporalLedger(db_path=str(db_file))
    
    # Log decision 1
    intent1 = Intent(intent_id="L1", actor_agent="agent", action_type="test", target_artifact="art", risk_tier=1)
    decision1 = Decision(intent_id="L1", status="COMMIT", timestamp="2026-05-26T10:00:00Z")
    ledger.log_decision(intent1, decision1)
    
    # Log decision 2
    intent2 = Intent(intent_id="L2", actor_agent="agent", action_type="test", target_artifact="art", risk_tier=1)
    decision2 = Decision(intent_id="L2", status="REJECT", timestamp="2026-05-26T10:10:00Z")
    ledger.log_decision(intent2, decision2)
    
    # Query as_of 10:05:00Z (should only find L1)
    history = ledger.get_history_as_of("2026-05-26T10:05:00Z")
    assert len(history) == 1
    assert history[0]["intent_id"] == "L1"
    
    # Query as_of 10:15:00Z (should find both)
    history2 = ledger.get_history_as_of("2026-05-26T10:15:00Z")
    assert len(history2) == 2
