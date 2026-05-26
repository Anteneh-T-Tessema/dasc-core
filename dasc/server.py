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

from fastapi import FastAPI, HTTPException, Depends, Security, WebSocket, WebSocketDisconnect, Response
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

from .policies import cybersecurity_policy, finance_policy, healthcare_policy, privacy_policy
from .policies.declarative import DeclarativePolicyEngine

kernel = Kernel(current_state_versions={"config.json": "v1.0.0"})
kernel.register_policy(cybersecurity_policy)
kernel.register_policy(finance_policy)
kernel.register_policy(healthcare_policy)
kernel.register_policy(privacy_policy)

# Declarative Policy Engine configuration
RULES_FILE = os.getenv("DASC_RULES_FILE", "dasc_rules.json")
RULES_DIR = os.getenv("DASC_RULES_DIR", "dasc_rules.d")
declarative_engine = DeclarativePolicyEngine()

if os.path.exists(RULES_FILE):
    try:
        declarative_engine.load_rules_from_file(RULES_FILE)
        print(f"[DASC] Loaded {len(declarative_engine.rules)} declarative rules from {RULES_FILE}")
    except Exception as e:
        print(f"[DASC] Error loading declarative rules: {e}")
else:
    default_rules = {
        "rules": [
            {
                "name": "Limit Big Spends",
                "condition": "payload.amount > 1000 and risk_tier < 3",
                "action": "REJECT",
                "reason": "TOO_EXPENSIVE"
            },
            {
                "name": "Nuke Command Verification",
                "condition": "action_type == 'NUKE'",
                "action": "ESCALATE",
                "reason": "NUKE_COMMAND_HITL"
            }
        ]
    }
    try:
        with open(RULES_FILE, "w") as f:
            json.dump(default_rules, f, indent=2)
        declarative_engine.load_rules_from_file(RULES_FILE)
        print(f"[DASC] Created and loaded default rules at {RULES_FILE}")
    except Exception as e:
        print(f"[DASC] Error writing default rules file: {e}")

if os.path.exists(RULES_DIR) and os.path.isdir(RULES_DIR):
    try:
        declarative_engine.load_rules_from_directory(RULES_DIR)
        print(f"[DASC] Loaded additional rules from folder {RULES_DIR}. Total rules: {len(declarative_engine.rules)}")
    except Exception as e:
        print(f"[DASC] Error loading rules from directory {RULES_DIR}: {e}")

kernel.register_policy(declarative_engine.evaluate_policies)

# Imperative dynamic policies
POLICIES_DIR = os.getenv("DASC_POLICIES_DIR", "dasc_policies.d")
if os.path.exists(POLICIES_DIR) and os.path.isdir(POLICIES_DIR):
    import importlib.util
    import sys
    print(f"[DASC] Scanning imperative policies directory: {POLICIES_DIR}")
    for root_dir, _, files in os.walk(POLICIES_DIR):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                file_path = os.path.join(root_dir, file)
                module_name = f"dasc_dynamic_policy_{os.path.splitext(file)[0]}"
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if callable(attr) and attr_name.endswith("_policy") and attr.__module__ == module_name:
                                kernel.register_policy(attr)
                except Exception as e:
                    print(f"[DASC] Error loading dynamic policy from {file_path}: {e}")

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

@app.get("/policies", dependencies=[Depends(get_api_key)])
def get_policies():
    """Returns the current list of active declarative rules."""
    return {"rules": declarative_engine.rules}

@app.post("/policies", dependencies=[Depends(get_api_key)])
def update_policies(rules_data: dict):
    """Updates the declarative rules config file and reloads it dynamically."""
    if "rules" not in rules_data or not isinstance(rules_data["rules"], list):
        raise HTTPException(status_code=400, detail="Invalid policies format: 'rules' list is required")
    
    # Validation
    for rule in rules_data["rules"]:
        if not isinstance(rule, dict) or "name" not in rule or "condition" not in rule or "action" not in rule or "reason" not in rule:
            raise HTTPException(status_code=400, detail="Invalid rule structure: name, condition, action, and reason are required")
        if rule["action"] not in ["COMMIT", "REJECT", "ESCALATE"]:
            raise HTTPException(status_code=400, detail="Invalid action: must be one of COMMIT, REJECT, ESCALATE")
            
    try:
        with open(RULES_FILE, "w") as f:
            json.dump(rules_data, f, indent=2)
        declarative_engine.load_rules_from_file(RULES_FILE)
        return {"status": "success", "rules": declarative_engine.rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rules: {str(e)}")

@app.get("/export", dependencies=[Depends(get_api_key)])
def export_ledger(format: str = "json", as_of: Optional[str] = None):
    """Exports compliance reports in JSON, CSV, or Markdown format."""
    import io
    import csv
    import time
    
    if as_of:
        if hasattr(ledger, "get_history_as_of"):
            history = ledger.get_history_as_of(as_of)
        else:
            history = ledger.get_history()
    else:
        history = ledger.get_history()
        
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Namespace", "Intent ID", "Actor Agent", "Status", "Reason Codes", "Timestamp", "Previous Hash", "Record Hash"])
        for r in history:
            writer.writerow([
                r.get("namespace", "default"),
                r["intent_id"],
                r["actor_agent"],
                r["status"],
                ", ".join(r["reason_codes"]) if isinstance(r["reason_codes"], list) else str(r["reason_codes"]),
                r["timestamp"],
                r["previous_hash"],
                r["record_hash"]
            ])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=dasc_compliance_report.csv"})
        
    elif format == "markdown":
        md = []
        md.append("# DASC Compliance Security Audit Report")
        md.append(f"\n* **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
        if as_of:
            md.append(f"* **Bitemporal Cutoff (As Of)**: {as_of}")
        md.append(f"* **Ledger Integrity Check**: {'PASS' if ledger.verify_integrity() else 'FAIL'}")
        
        md.append("\n## Audit Trail Summary")
        total = len(history)
        commits = len([h for h in history if h["status"] == "COMMIT"])
        rejections = len([h for h in history if h["status"] == "REJECT"])
        escalations = len([h for h in history if h["status"] == "ESCALATE"])
        
        md.append(f"* **Total Evaluated Intents**: {total}")
        md.append(f"* **Total Commits**:           {commits}")
        md.append(f"* **Total Rejections**:        {rejections}")
        md.append(f"* **Total Escalations**:       {escalations}")
        
        md.append("\n## Ledger Records")
        md.append("| Timestamp | Intent ID | Agent | Status | Reasons | Record Hash |")
        md.append("| --- | --- | --- | --- | --- | --- |")
        for r in history:
            reasons_str = ", ".join(r["reason_codes"]) if isinstance(r["reason_codes"], list) else str(r["reason_codes"])
            md.append(f"| {r['timestamp']} | `{r['intent_id']}` | `{r['actor_agent']}` | **{r['status']}** | {reasons_str or 'None'} | `{r['record_hash'][:8]}` |")
            
        return Response(content="\n".join(md), media_type="text/markdown", headers={"Content-Disposition": "attachment; filename=dasc_compliance_report.md"})
        
    else:  # default to json
        return {"history": history}

# Serve static dashboard files if they exist in the package
from fastapi.staticfiles import StaticFiles
dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

