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
        
    def _get_last_run_mode(self):
        if not self.db_path or not os.path.exists(self.db_path):
            return None, None
            
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT crawler_mode, status FROM runs ORDER BY started_at DESC LIMIT 1")
            row = c.fetchone()
            conn.close()
            if row:
                return row[0], row[1]
        except Exception:
            pass
        return None, None

    def get_current(self, check_network=False):
        svc = SessionService()
        mode = svc.get_mode()
        
        # 1. Base status based on configuration
        status = "NOT_CONFIGURED"
        if mode == SESSION_CORRUPTED:
            status = "INVALID"
        elif mode in (SESSION_PERSISTENT, SESSION_TEMPORARY, SESSION_EPHEMERAL):
            status = "CONFIGURED"
            
        token = svc.get_token()
        
        result = {
            "configured": token is not None,
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
        
        if not token:
            result["action_required"] = "CONFIG_REQUIRED"
            result["effective"] = False
            return result
            
        # 2. Check network if explicitly requested
        if check_network:
            try:
                data = fetch_account_profile(token)
                if data == "RATE_LIMIT":
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
        else:
            # 3. Infer from DB (last run)
            last_mode, last_status = self._get_last_run_mode()
            if last_mode == "ZONE_INVENTORY" and last_status == "COMPLETED":
                result["status"] = "VALID"
            elif last_mode == "SEARCH_DISCOVERY" and status == "CONFIGURED":
                # If it's configured but we are running in SEARCH_DISCOVERY, it means it's expired or falling back
                # But wait, SEARCH_DISCOVERY could be the user's manual choice? No, the CLI always prefers ZONE if auth.
                result["status"] = "EXPIRED"
            elif last_status == "PARTIAL":
                # A partial run might have been interrupted by 401
                # But we can't be 100% sure unless we know the error code.
                # Let's assume CONFIGURED for now.
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

