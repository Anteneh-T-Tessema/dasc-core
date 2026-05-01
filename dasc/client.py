import requests
from typing import Dict, Any, Optional
from .schemas import Intent, Decision

class DASCClient:
    """
    A remote client for the DASC Control Plane.
    Allows agents to submit intents over the network.
    """
    def __init__(self, api_url: str = "http://localhost:8000", api_key: str = "dasc-dev-key-123"):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-API-KEY": self.api_key}

    def evaluate(self, intent: Intent) -> Decision:
        """
        Sends an intent to the remote DASC server for evaluation.
        """
        response = requests.post(
            f"{self.api_url}/evaluate",
            json=intent.model_dump(),
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return Decision(**response.json())
        else:
            # Handle API errors gracefully
            return Decision(
                intent_id=intent.intent_id,
                status="REJECT",
                reason_codes=[f"REMOTE_API_ERROR: {response.status_code}", response.text]
            )

    def get_ledger(self, namespace: Optional[str] = None):
        """Retrieves history from the remote server."""
        params = {}
        if namespace:
            params["namespace"] = namespace
        response = requests.get(
            f"{self.api_url}/ledger", 
            params=params, 
            headers=self.headers,
            timeout=10
        )
        return response.json()
