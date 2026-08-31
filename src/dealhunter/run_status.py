def normalize_run_status(raw_status: str) -> str:
    """
    Normalizes a raw provider status to a canonical DealHunter run status.
    Canonical statuses: 'SUCCESS', 'PARTIAL', 'FAILED', 'RUNNING'
    """
    if not raw_status:
        return "FAILED"
    
    r = raw_status.upper()
    
    if r in ("SUCCESS", "COMPLETED", "COMPLETE", "DONE"):
        return "SUCCESS"
        
    if r in ("PARTIAL", "REQUEST_BUDGET_REACHED", "TIMEOUT", "SESSION_EXPIRED", "SKIPPED"):
        return "PARTIAL"
        
    if r in ("RUNNING",):
        return "RUNNING"
        
    # FAILED, ERROR, RETRYABLE, INVALID_RESPONSE, NETWORK_ERROR, etc.
    return "FAILED"
