import json
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .kernel import Kernel
from .ledger import BitemporalLedger
from .schemas import Decision, Intent

app = FastAPI(title="DASC Control Plane")
ledger = BitemporalLedger()
kernel = Kernel()

class HITLApproval(BaseModel):
    intent_id: str
    approved: bool
    approver_id: str
    comments: Optional[str] = None

@app.get("/ledger")
def get_ledger(limit: int = 50):
    """Returns the bitemporal ledger history."""
    return ledger.get_history()[:limit]

@app.get("/integrity")
def check_integrity():
    """Verifies the hash-chain integrity of the ledger."""
    is_intact = ledger.verify_integrity()
    return {"status": "intact" if is_intact else "compromised", "valid": is_intact}

@app.post("/approve")
def approve_intent(approval: HITLApproval):
    """
    Manually approves or rejects an escalated intent.
    In a real system, this would update the state and record a new decision.
    """
    history = ledger.get_history()
    target = next((item for item in history if item["intent_id"] == approval.intent_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    if target["status"] != "ESCALATE":
        raise HTTPException(status_code=400, detail="Only escalated intents can be manually approved")
    
    # Record the manual decision
    # We'll create a new commitment representing the human approval
    new_status = "COMMIT" if approval.approved else "REJECT"
    print(f"[HITL] Intent {approval.intent_id} {new_status} by {approval.approver_id}")
    
    return {"status": "success", "new_status": new_status}

@app.get("/stats")
def get_stats():
    """Returns summary statistics for the dashboard."""
    history = ledger.get_history()
    return {
        "total": len(history),
        "commits": len([i for i in history if i["status"] == "COMMIT"]),
        "rejections": len([i for i in history if i["status"] == "REJECT"]),
        "escalations": len([i for i in history if i["status"] == "ESCALATE"]),
    }
