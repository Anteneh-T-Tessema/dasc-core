from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import datetime

class Evidence(BaseModel):
    evidence_id: str
    source_type: str
    span: Dict[str, Any]  # e.g., {"line": 42}
    content_hash: Optional[str] = None

class Intent(BaseModel):
    intent_id: str
    actor_agent: str
    namespace: str = Field(default="default", description="Isolation boundary for multi-tenant support")
    action_type: str
    target_artifact: str
    risk_tier: int = Field(default=1, ge=1, le=4)
    evidence: List[Evidence] = []
    
    # Optimistic Concurrency Control (OCC)
    state_version_vector: Optional[Dict[str, str]] = None
    
    # Non-idempotent action fallback
    compensation_plan: Optional[Dict[str, str]] = None

class Decision(BaseModel):
    intent_id: str
    status: str # COMMIT, REJECT, ESCALATE
    reason_codes: List[str] = []
    suggestions: List[str] = [] # Actionable advice for recovery
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
