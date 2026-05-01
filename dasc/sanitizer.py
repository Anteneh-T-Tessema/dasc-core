import re
from typing import Any, Dict, Union

# Common patterns for sensitive data
SENSITIVE_PATTERNS = {
    "api_key": r"(?:api_key|apikey|secret|token|password|auth_key)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-_]{16,})['\"]?",
    "jwt": r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
    "private_key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----"
}

def sanitize_content(content: str) -> str:
    """
    Scrubs sensitive patterns from a string.
    """
    sanitized = content
    for label, pattern in SENSITIVE_PATTERNS.items():
        # Replace the sensitive match with a placeholder [SCRUBBED]
        sanitized = re.sub(pattern, lambda m: m.group(0).replace(m.group(1) if len(m.groups()) > 0 else m.group(0), f"[SCRUBBED_{label.upper()}]"), sanitized)
    return sanitized

def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively scrubs sensitive patterns from a dictionary.
    """
    import json
    # Simple way: convert to JSON, sanitize string, convert back
    dump = json.dumps(data)
    sanitized_dump = sanitize_content(dump)
    return json.loads(sanitized_dump)
