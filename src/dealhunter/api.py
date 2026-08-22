import urllib.request
import urllib.error
import json
from .errors import DealHunterError, classify_error

def fetch_unified_search(query, lat, lng, auth_token=None):
    url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
    payload = json.dumps({"query": query, "lat": lat, "lng": lng, "limit": 1000}).encode('utf-8')
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.rappi.com.mx"
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
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
    # The /profile endpoint is consistently blocked by Cloudflare WAF for automated clients (returns 403).
    # To demonstrate positive authentication, we use the unified-search endpoint.
    # An anonymous request returns HTTP 200 but stores have empty 'eta'.
    # An authenticated request with a VALID token returns HTTP 200 and populates 'eta'.
    # An authenticated request with an INVALID/EXPIRED token returns HTTP 401.
    url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }
    
    import json
    # Use generic payload (CDMX) with a common query to guarantee store results
    body = json.dumps({"is_prime": False, "query": "coca cola", "lat": 19.432608, "lng": -99.133209, "limit": 10}).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            stores = data.get("stores", [])
            
            # Positive authentication evidence: ETA is populated.
            is_authenticated = any(store.get("eta") for store in stores)
            
            if is_authenticated:
                return {"market": "MX", "prime": False, "note": "Validated via unified-search (eta present)"}
            else:
                return "UNVERIFIED"
                
    except urllib.error.HTTPError as e:
        from .errors import DealHunterError, classify_error
        if e.code == 401:
            raise DealHunterError("ACCOUNT_SESSION_UNAVAILABLE", "Invalid or expired session", recoverable=False)
        elif e.code in [429, 1015]:
            return "RATE_LIMIT"
            
        raise classify_error(e)
    except Exception as e:
        from .errors import classify_error
        raise classify_error(e)

def fetch_restaurant_categories(store_id):
    import re
    url = f"https://www.rappi.com.mx/restaurantes/{store_id}"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if not m:
                return {}
            data = json.loads(m.group(1))
            
            # Find corridors
            corridors = []
            def extract_corridors(d):
                if isinstance(d, dict):
                    if 'corridors' in d and isinstance(d['corridors'], list):
                        corridors.extend(d['corridors'])
                    else:
                        for v in d.values():
                            extract_corridors(v)
                elif isinstance(d, list):
                    for v in d:
                        extract_corridors(v)
            
            extract_corridors(data)
            
            category_map = {}
            for c in corridors:
                cat_name = c.get("name", "")
                if not cat_name:
                    continue
                for p in c.get("products", []):
                    pid = p.get("id") or p.get("product_id")
                    if pid:
                        category_map[str(pid)] = cat_name
            return category_map
    except Exception as e:
        return {}
