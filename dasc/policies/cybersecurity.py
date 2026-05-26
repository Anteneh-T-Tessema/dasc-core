import json
from ..schemas import Intent

def cybersecurity_policy(intent: Intent):
    """
    Cybersecurity Policy
    Focuses on preventing Command Injection and Unauthorized Path Access.
    """
    dangerous_commands = ["rm -rf", "mkfs", "dd", "sh ", "bash ", "curl ", "wget "]
    restricted_paths = ["/etc/shadow", "/etc/passwd", "~/.ssh", "/var/run/docker.sock"]

    # Convert payload to string representation for content searching
    payload_dict = intent.payload if hasattr(intent, "payload") else {}
    if not payload_dict:
        # Check if payload might be passed under another field or we can check the whole model
        payload_dict = getattr(intent, "payload", {}) or {}
    
    payload_str = json.dumps(payload_dict).lower()

    # 1. Check for dangerous shell commands
    for cmd in dangerous_commands:
        if cmd in payload_str:
            return False, f"DANGEROUS_COMMAND_DETECTED: {cmd}"

    # 2. Check for restricted system paths
    for path in restricted_paths:
        if path in payload_str:
            return False, f"RESTRICTED_PATH_ACCESS: {path}"

    # 3. Prevent Tier 1 agents from doing Tier 3+ actions
    if "untrusted" in intent.actor_agent.lower() and intent.risk_tier >= 3:
        return False, "PRIVILEGE_MISMATCH: Untrusted agent attempted Tier 3 action"

    return True, ""
