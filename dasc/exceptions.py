class DASCError(Exception):
    """Base exception for all DASC related errors."""
    def __init__(self, message, intent_id=None):
        super().__init__(message)
        self.intent_id = intent_id

class SchemaValidationError(DASCError):
    """Raised when an intent fails basic structural validation."""
    pass

class OCCConflictError(DASCError):
    """Raised when the state version has drifted (TOCTOU)."""
    pass

class PolicyViolationError(DASCError):
    """Raised when an action violates a risk policy (e.g., missing compensation plan)."""
    pass

class TaintDetectedError(DASCError):
    """Raised when evidence flow control detects untrusted data."""
    pass

class EscalationRequired(DASCError):
    """Raised when an action requires external human intervention."""
    pass
