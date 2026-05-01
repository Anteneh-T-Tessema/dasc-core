from typing import Any, Type, Optional, Dict
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from ..kernel import Kernel
from ..schemas import Intent

class DASCActionSchema(BaseModel):
    """Input schema for DASC Commitment Tool."""
    intent_id: str = Field(..., description="Unique ID for this specific action.")
    actor_agent: str = Field(..., description="The name/role of the agent performing the action.")
    action_type: str = Field(..., description="The verb describing the action.")
    target_artifact: str = Field(..., description="The object being acted upon.")
    risk_tier: int = Field(default=1, description="Risk level from 1-4.")
    state_version: Optional[str] = Field(None, description="Current version/hash of the target.")
    compensation: Optional[str] = Field(None, description="What to do if this fails.")

class CrewDASCConnector(BaseTool):
    name: str = "dasc_safety_kernel"
    description: str = (
        "Mandatory tool for committing actions to the authoritative system. "
        "Agents must provide intent ID, risk tier, and evidence to pass the safety boundary."
    )
    args_schema: Type[BaseModel] = DASCActionSchema
    kernel: Kernel = Field(..., exclude=True) # Exclude from Pydantic serialization

    def _run(self, **kwargs: Any) -> str:
        # Map CrewAI tool arguments to DASC Intent
        intent = Intent(
            intent_id=kwargs.get("intent_id"),
            actor_agent=kwargs.get("actor_agent"),
            action_type=kwargs.get("action_type"),
            target_artifact=kwargs.get("target_artifact"),
            risk_tier=kwargs.get("risk_tier", 1),
            state_version_vector={kwargs.get("target_artifact"): kwargs.get("state_version")} if kwargs.get("state_version") else None,
            compensation_plan={"undo": kwargs.get("compensation")} if kwargs.get("compensation") else None
        )
        
        decision = self.kernel.evaluate(intent)
        
        if decision.status == "COMMIT":
            return f"DASC: AUTHORIZED. Action {kwargs.get('intent_id')} has been committed to the ledger."
        elif decision.status == "ESCALATE":
            return f"DASC: ESCALATED. Action {kwargs.get('intent_id')} requires human approval."
        else:
            return f"DASC: REJECTED. Safety violation: {', '.join(decision.reason_codes)}"

# Example Usage:
# kernel = Kernel()
# safety_tool = CrewDASCConnector(kernel=kernel)
# agent = Agent(role="Executor", tools=[safety_tool], ...)
