import urllib.request
import urllib.error
import json

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
    except Exception as e:
        pass
    return None
