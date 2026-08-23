import sys, os; sys.path.insert(0, os.path.abspath("src"))
import urllib.request, json
from dealhunter.auth import RappiSessionProvider

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.rappi.com.mx"
}
prov = RappiSessionProvider()
if prov.context and prov.context._access_token:
    headers["Authorization"] = f"Bearer {prov.context._access_token}"

endpoints = [
    ("https://services.mxgrability.rappi.com/api/web-gateway/web/home/v2", "GET", None),
    ("https://services.mxgrability.rappi.com/api/web-gateway/web/home/v2", "POST", {"lat": 19.4326, "lng": -99.1332}),
    ("https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search", "POST", {"lat": 19.4326, "lng": -99.1332, "query": "a", "limit": 1}),
]

for url, method, payload in endpoints:
    try:
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"{method} {url} -> {resp.getcode()}")
    except Exception as e:
        code = getattr(e, 'code', 'N/A')
        print(f"{method} {url} -> {code}")
