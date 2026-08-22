import os
import json
import sqlite3
from .api import fetch_account_profile
from .errors import DealHunterError
from .secret_store import SessionService, SESSION_NOT_CONFIGURED, SESSION_CORRUPTED, SESSION_PERSISTENT, SESSION_TEMPORARY, SESSION_EPHEMERAL, SESSION_EXPIRED
from datetime import datetime

class SessionStatus:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def get_current(self, check_network=False):
        svc = SessionService()
        mode = svc.get_mode()
        is_expired = getattr(svc, '_is_expired', False)

        # 1. Base status based on configuration
        status = "NOT_CONFIGURED"
        if mode == SESSION_CORRUPTED:
            status = "INVALID"
        elif is_expired:
            status = "EXPIRED"
        elif mode in (SESSION_PERSISTENT, SESSION_TEMPORARY, SESSION_EPHEMERAL):
            status = "CONFIGURED"

        token = svc.get_token()
        raw_token = getattr(svc, 'get_raw_token', svc.get_token)()

        result = {
            "configured": raw_token is not None,
            "status": status,
            "mode": mode,
            "source": mode,
            "last_validated_at": None,
            "action_required": None,
            "market": "UNKNOWN",
            "region": "UNKNOWN",
            "has_prime": False,
            "prime_type": "NONE"
        }

        if not raw_token:
            result["action_required"] = "CONFIG_REQUIRED"
            result["effective"] = False
            return result

        # 2. Check network if explicitly requested and not already expired
        if check_network and not is_expired and token:
            try:
                data = fetch_account_profile(token)
                if data in ("RATE_LIMIT", "UNVERIFIED"):
                    # We can't be sure, assume configured
                    pass
                elif not data:
                    result["status"] = "EXPIRED"
                    svc.mark_expired()
                else:
                    result["status"] = "VALID"
                    result["market"] = data.get("market", "UNKNOWN")
                    result["region"] = data.get("region", "UNKNOWN")
                    result["has_prime"] = data.get("prime", False) or data.get("has_prime", False)
                    result["prime_type"] = data.get("prime_type", "NONE")
                    result["last_validated_at"] = datetime.now().isoformat()
            except DealHunterError as e:
                if e.code == "ACCOUNT_SESSION_UNAVAILABLE":
                    result["status"] = "EXPIRED"
                    svc.mark_expired()
            except Exception:
                pass

        if result["status"] == "EXPIRED":
            result["action_required"] = "UPDATE_SESSION"

        # Determine effective session (valid enough to try)
        result["effective"] = (result["status"] in ("VALID", "CONFIGURED"))
        return result


        # 2. Check network if explicitly requested
        if check_network:
            try:
                data = fetch_account_profile(token)
                if data in ("RATE_LIMIT", "UNVERIFIED"):
                    # We can't be sure, assume configured
                    pass
                elif not data:
                    result["status"] = "EXPIRED"
                else:
                    result["status"] = "VALID"
                    result["market"] = data.get("market", "UNKNOWN")
                    result["region"] = data.get("region", "UNKNOWN")
                    result["has_prime"] = data.get("prime", False) or data.get("has_prime", False)
                    result["prime_type"] = data.get("prime_type", "NONE")
                    result["last_validated_at"] = datetime.now().isoformat()
            except DealHunterError as e:
                if e.code == "ACCOUNT_SESSION_UNAVAILABLE":
                    result["status"] = "EXPIRED"
                    svc.mark_expired()
            except Exception:
                pass

        if result["status"] == "EXPIRED":
            result["action_required"] = "UPDATE_SESSION"

        # Determine effective session (valid enough to try)
        result["effective"] = (result["status"] in ("VALID", "CONFIGURED"))
        return result

def get_account_token(config=None):
    svc = SessionService()
    return svc.get_token()

def get_account_status(config=None, check_network=True):
    # Compatibility with older calls
    resolver = SessionStatus()
    res = resolver.get_current(check_network=check_network)
    return res

