import json
import logging
import urllib.request
from typing import List, Dict, Any
from .schemas import Intent, Decision

logger = logging.getLogger("dasc.webhooks")

class WebhookDispatcher:
    def __init__(self, webhook_urls: List[str] = None):
        self.webhook_urls = webhook_urls or []

    def dispatch_escalation(self, intent: Intent, decision: Decision):
        """
        Sends a POST request to all registered webhooks for an ESCALATE decision.
        """
        payload = {
            "event": "DASC_ESCALATION_REQUIRED",
            "intent": intent.model_dump(),
            "decision": decision.model_dump(),
            "timestamp": decision.timestamp
        }
        
        data = json.dumps(payload).encode('utf-8')
        
        for url in self.webhook_urls:
            try:
                req = urllib.request.Request(
                    url, 
                    data=data, 
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    logger.info(f"Successfully dispatched escalation to {url} (Status: {response.status})")
            except Exception as e:
                logger.error(f"Failed to dispatch webhook to {url}: {str(e)}")

# Example usage:
# dispatcher = WebhookDispatcher(["https://hooks.slack.com/services/..."])
# if decision.status == "ESCALATE":
#     dispatcher.dispatch_escalation(intent, decision)
