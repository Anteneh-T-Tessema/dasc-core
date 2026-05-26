import json
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .kernel import Kernel
from .ledger import BitemporalLedger
from .schemas import Decision, Intent

import os
from .persistence import PostgresLedger

from fastapi import FastAPI, HTTPException, Depends, Security, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from .persistence import PostgresLedger
from .webhooks import NotificationManager

app = FastAPI(title="DASC Control Plane")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket active connection pool
active_connections: List[WebSocket] = []

async def broadcast_update(message: dict):
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            pass

# Notification Configuration
notifier = NotificationManager(os.getenv("SLACK_WEBHOOK_URL"))

# Security Configuration
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)
MASTER_API_KEY = os.getenv("DASC_MASTER_KEY", "dasc-dev-key-123")

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != MASTER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return api_key

# Database Selection Logic
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    ledger = PostgresLedger(DATABASE_URL)
    print("[DASC] Using PostgreSQL Ledger")
else:
    ledger = BitemporalLedger()
    print("[DASC] Using Local SQLite Ledger")

from .policies import cybersecurity_policy, finance_policy, healthcare_policy

kernel = Kernel(current_state_versions={"config.json": "v1.0.0"})
kernel.register_policy(cybersecurity_policy)
kernel.register_policy(finance_policy)
kernel.register_policy(healthcare_policy)

class HITLApproval(BaseModel):
    intent_id: str
    approved: bool
    approver_id: str
    comments: Optional[str] = None

@app.get("/ledger", dependencies=[Depends(get_api_key)])
def get_ledger(limit: int = 50, as_of: Optional[str] = None):
    """Returns the bitemporal ledger history."""
    if as_of:
        # Check if get_history_as_of is implemented, otherwise fallback
        if hasattr(ledger, "get_history_as_of"):
            return ledger.get_history_as_of(as_of)[:limit]
    return ledger.get_history()[:limit]

@app.get("/integrity", dependencies=[Depends(get_api_key)])
def check_integrity():
    """Verifies the hash-chain integrity of the ledger."""
    is_intact = ledger.verify_integrity()
    return {"status": "intact" if is_intact else "compromised", "valid": is_intact}

@app.post("/approve", dependencies=[Depends(get_api_key)])
async def approve_intent(approval: HITLApproval):
    """
    Manually approves or rejects an escalated intent.
    Records the manual decision in the ledger and broadcasts it.
    """
    history = ledger.get_history()
    target = next((item for item in history if item["intent_id"] == approval.intent_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    if target["status"] != "ESCALATE":
        raise HTTPException(status_code=400, detail="Only escalated intents can be manually approved")
    
    new_status = "COMMIT" if approval.approved else "REJECT"
    print(f"[HITL] Intent {approval.intent_id} {new_status} by {approval.approver_id}")
    
    # Save decision in bitemporal ledger
    intent_dict = json.loads(target["intent_json"])
    intent = Intent(**intent_dict)
    decision = Decision(
        intent_id=approval.intent_id,
        status=new_status,
        reason_codes=[f"MANUAL_{new_status}_BY_{approval.approver_id}"],
        suggestions=[]
    )
    ledger.log_decision(intent, decision)
    
    # Broadcast HITL update to dashboard
    await broadcast_update({
        "type": "DECISION_UPDATED",
        "intent_id": approval.intent_id,
        "status": new_status,
        "decision": decision.model_dump()
    })
    
    return {"status": "success", "new_status": new_status}

@app.post("/evaluate", response_model=Decision, dependencies=[Depends(get_api_key)])
async def evaluate_intent(intent: Intent):
    """
    Remote endpoint for distributed agents to submit intents 
    to the centralized DASC Safety Boundary.
    """
    decision = kernel.evaluate(intent)
    
    # Broadcast evaluation to WebSocket clients
    await broadcast_update({
        "type": "INTENT_EVALUATED",
        "intent": intent.model_dump(),
        "decision": decision.model_dump()
    })
    
    # Trigger active alerting for sensitive events
    if decision.status != "COMMIT":
        notifier.notify(intent, decision)
        
    return decision

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection open and accept inbound messages
            data = await websocket.receive_json()
            if data.get("type") in ["APPROVE", "DENY"]:
                intent_id = data.get("intent_id")
                approved = data.get("type") == "APPROVE"
                approver = data.get("approver", "DASC_ADMIN_WS")
                
                history = ledger.get_history()
                target = next((item for item in history if item["intent_id"] == intent_id), None)
                if target and target["status"] == "ESCALATE":
                    new_status = "COMMIT" if approved else "REJECT"
                    intent_dict = json.loads(target["intent_json"])
                    intent = Intent(**intent_dict)
                    decision = Decision(
                        intent_id=intent_id,
                        status=new_status,
                        reason_codes=[f"MANUAL_{new_status}_BY_{approver}"],
                        suggestions=[]
                    )
                    ledger.log_decision(intent, decision)
                    await broadcast_update({
                        "type": "DECISION_UPDATED",
                        "intent_id": intent_id,
                        "status": new_status,
                        "decision": decision.model_dump()
                    })
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/stats", dependencies=[Depends(get_api_key)])
def get_stats():
    """Returns summary statistics for the dashboard."""
    history = ledger.get_history()
    return {
        "total": len(history),
        "commits": len([i for i in history if i["status"] == "COMMIT"]),
        "rejections": len([i for i in history if i["status"] == "REJECT"]),
        "escalations": len([i for i in history if i["status"] == "ESCALATE"]),
    }

# Serve static dashboard files if they exist in the package
from fastapi.staticfiles import StaticFiles
dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

