import sys, os; sys.path.insert(0, os.path.abspath("src"))
import urllib.request, json
from dealhunter.auth import RappiSessionProvider

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Rappi/7.1.189 (Android 11; Google Pixel 3)",
    "DeviceID": "1234567890",
    "App-Version": "7.1.189",
    "x-guest-api-key": "guest"
}
prov = RappiSessionProvider()
if prov.context and prov.context._access_token:
    headers["Authorization"] = f"Bearer {prov.context._access_token}"

endpoints = [
    "https://services.mxgrability.rappi.com/api/ms/discovery/v2/restaurants",
    "https://services.mxgrability.rappi.com/api/ms/discovery/v1/restaurants",
    "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
]
for url in endpoints:
    try:
        req = urllib.request.Request(url, data=json.dumps({"lat": 19.4326, "lng": -99.1332}).encode('utf-8'), headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"POST {url} -> {resp.getcode()}")
    except Exception as e:
        code = getattr(e, 'code', 'N/A')
        print(f"POST {url} -> {code}")
