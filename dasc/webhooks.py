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
        
        import requests
        for url in self.webhook_urls:
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=5
                )
                response.raise_for_status()
                logger.info(f"Successfully dispatched escalation to {url} (Status: {response.status_code})")
            except Exception as e:
                logger.error(f"Failed to dispatch webhook to {url}: {str(e)}")

class NotificationManager:
    """
    Handles formatting and dispatching DASC events to external 
    comms channels like Slack or Discord.
    """
    def __init__(self, slack_webhook_url: str = None):
        self.slack_url = slack_webhook_url

    def format_slack_message(self, intent: Intent, decision: Decision) -> Dict[str, Any]:
        """Formats a DASC escalation into a Slack Block Kit message."""
        status_emoji = "⚠️" if decision.status == "ESCALATE" else "🚫"
        
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{status_emoji} DASC Safety Alert: {decision.status}"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Intent ID:*\n{intent.intent_id}"},
                        {"type": "mrkdwn", "text": f"*Agent:*\n{intent.actor_agent}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Proposed Action:*\n`{intent.action_type}` on `{intent.target_artifact}`"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Reason Codes:*\n{', '.join(decision.reason_codes)}"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Recovery Advice:*\n{', '.join(decision.suggestions)}"}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve (HITL)"},
                            "style": "primary",
                            "value": intent.intent_id
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Reject (HITL)"},
                            "style": "danger",
                            "value": intent.intent_id
                        }
                    ]
                }
            ]
        }

    def notify(self, intent: Intent, decision: Decision):
        """Dispatches the notification if a webhook is configured."""
        if not self.slack_url:
            return

        import requests
        try:
            payload = self.format_slack_message(intent, decision)
            requests.post(self.slack_url, json=payload, timeout=5)
            logger.info(f"DASC alert dispatched to Slack for {intent.intent_id}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
