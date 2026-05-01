from typing import Optional, Type, Any, Dict
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from ..schemas import Intent, Decision
from ..kernel import Kernel

class DASCCommitSchema(BaseModel):
    intent_id: str = Field(description="Unique identifier for the intent")
    actor_agent: str = Field(description="Name/ID of the agent performing the action")
    action_type: str = Field(description="The type of action (e.g., 'update_file', 'api_call')")
    target_artifact: str = Field(description="The resource being modified")
    risk_tier: int = Field(default=1, description="Risk level from 1 to 4")
    state_version_vector: Optional[Dict[str, str]] = Field(default=None, description="Current version of the target artifact")
    compensation_plan: Optional[Dict[str, str]] = Field(default=None, description="Fallback plan if the action fails")

class DASCCommitTool(BaseTool):
    name: str = "dasc_commit_tool"
    description: str = "Use this tool to commit a structured intent to the DASC safety kernel. This is the only way to perform external actions."
    args_schema: Type[BaseModel] = DASCCommitSchema
    kernel: Kernel

    def _run(
        self, 
        intent_id: str,
        actor_agent: str,
        action_type: str,
        target_artifact: str,
        risk_tier: int = 1,
        state_version_vector: Optional[Dict[str, str]] = None,
        compensation_plan: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """Use the tool."""
        intent = Intent(
            intent_id=intent_id,
            actor_agent=actor_agent,
            action_type=action_type,
            target_artifact=target_artifact,
            risk_tier=risk_tier,
            state_version_vector=state_version_vector,
            compensation_plan=compensation_plan
        )
        
        decision = self.kernel.evaluate(intent)
        
        if decision.status == "COMMIT":
            return f"COMMIT_SUCCESS: Intent {intent_id} has been authorized and recorded."
        else:
            reasons = ", ".join(decision.reason_codes)
            return f"REJECTED: Intent {intent_id} failed safety checks. Reasons: {reasons}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Use the tool asynchronously."""
        # For MVP, just use synchronous run
        return self._run(*args, **kwargs)
