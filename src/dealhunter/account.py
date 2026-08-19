import os
from .api import fetch_account_profile
from .errors import DealHunterError

def get_account_token(config=None):
    # Ensure tokens are never read from config files to avoid persistence
    return os.environ.get("RAPPI_BEARER_TOKEN")

def sanitize_account_data(data):
    if not isinstance(data, dict):
        return {}
        
    safe_data = {
        "status": "VALID",
        "market": data.get("market", "UNKNOWN"),
        "region": data.get("region", "UNKNOWN"),
        "has_prime": data.get("prime", False) or data.get("has_prime", False),
        "prime_type": data.get("prime_type", "NONE")
    }
    
    # Check context/benefits if available in a safe way
    benefits = data.get("benefits", {})
    if isinstance(benefits, dict):
        safe_data["active_promos"] = len(benefits.get("promotions", []))
    
    # We purposefully exclude and discard:
    # email, phone, personal names, addresses, payment methods, raw tokens
    
    return safe_data

def get_account_status(config=None):
    token = get_account_token(config)
    if not token:
        return {"status": "NOT_CONFIGURED"}
        
    try:
        data = fetch_account_profile(token)
        if data == "RATE_LIMIT":
            raise DealHunterError("HTTP_429", "Rate limit exceeded checking account", recoverable=False)
        if not data:
            raise DealHunterError("INVALID_RESPONSE", "Empty response from account profile", recoverable=False)
            
        return sanitize_account_data(data)
    except DealHunterError as e:
        if e.code == "ACCOUNT_SESSION_UNAVAILABLE":
            return {"status": "UNAVAILABLE", "error": str(e)}
        raise e
