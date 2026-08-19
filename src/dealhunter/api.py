import urllib.request
import urllib.error
import json
from .errors import DealHunterError, classify_error

def fetch_unified_search(query, lat, lng):
    url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
    payload = json.dumps({"query": query, "lat": lat, "lng": lng, "limit": 1000}).encode('utf-8')
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in [429, 1015]:
            return "RATE_LIMIT"
        raise classify_error(e)
    except (urllib.error.URLError, TimeoutError) as e:
        raise classify_error(e)
    except json.JSONDecodeError as e:
        raise classify_error(e)
    except Exception as e:
        raise classify_error(e)
    return None

def fetch_account_profile(token):
    # NOT_SAFE_TO_IMPLEMENT: Automatic token extraction from the Android app
    # requires root access or invasive bypasses.
    # This function expects a user-provided token.
    url = "https://services.mxgrability.rappi.com/api/ms/users/profile"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            from .errors import DealHunterError
            raise DealHunterError("ACCOUNT_SESSION_UNAVAILABLE", "Invalid or expired session", recoverable=False)
        if e.code in [429, 1015]:
            return "RATE_LIMIT"
        raise classify_error(e)
    except Exception as e:
        raise classify_error(e)
