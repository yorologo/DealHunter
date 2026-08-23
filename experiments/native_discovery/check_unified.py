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

url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"

payloads = [
    {"lat": 19.4326, "lng": -99.1332, "limit": 100},
    {"lat": 19.4326, "lng": -99.1332, "query": "", "limit": 100},
    {"lat": 19.4326, "lng": -99.1332, "query": "*", "limit": 100}
]

for p in payloads:
    try:
        req = urllib.request.Request(url, data=json.dumps(p).encode('utf-8'), headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=5)
        res = json.loads(resp.read().decode())
        stores = res.get('stores', [])
        print(f"Payload {p} -> 200, stores: {len(stores)}")
    except Exception as e:
        code = getattr(e, 'code', 'N/A')
        print(f"Payload {p} -> {code}")
