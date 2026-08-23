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

payload = {"lat": 19.4326, "lng": -99.1332}
endpoints = [
    "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/search",
    "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/restaurants",
    "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/stores",
    "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/catalogs"
]
for url in endpoints:
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"POST {url} -> {resp.getcode()}")
    except Exception as e:
        code = getattr(e, 'code', 'N/A')
        print(f"POST {url} -> {code}")
url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/search?lat=19.4326&lng=-99.1332"
try:
    req = urllib.request.Request(url, headers=headers, method="GET")
    resp = urllib.request.urlopen(req, timeout=5)
    print(f"GET {url} -> {resp.getcode()}")
except Exception as e:
    code = getattr(e, 'code', 'N/A')
    print(f"GET {url} -> {code}")
