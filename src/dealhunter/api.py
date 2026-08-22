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
    # Try to fetch profile, but fallback if WAF blocks it (403)
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
        from .errors import DealHunterError, classify_error
        if e.code == 401:
            raise DealHunterError("ACCOUNT_SESSION_UNAVAILABLE", "Invalid or expired session", recoverable=False)
        elif e.code == 403:
            # WAF might block /profile. Validate token by hitting search API
            search_url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
            search_req = urllib.request.Request(search_url, headers=headers, method="POST")
            try:
                urllib.request.urlopen(search_req, timeout=10)
            except urllib.error.HTTPError as se:
                if se.code == 401:
                    raise DealHunterError("ACCOUNT_SESSION_UNAVAILABLE", "Invalid or expired session", recoverable=False)
                # 400 Bad Request is expected because we didn't send a payload, but it proves the token was accepted!
                elif se.code == 400 or se.code == 403:
                    return {"market": "UNKNOWN", "prime": False, "note": "Validated via fallback"}
            except Exception:
                pass
            return {"market": "UNKNOWN", "prime": False, "note": "Validated via fallback (403)"}
        
        if e.code in [429, 1015]:
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
