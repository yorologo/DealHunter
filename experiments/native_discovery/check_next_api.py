import urllib.request, json
import sys, os; sys.path.insert(0, os.path.abspath("src"))
from dealhunter.auth import RappiSessionProvider

LAT = 19.432608
LNG = -99.133209

headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.rappi.com.mx",
    "x-guest-api-key": "guest",
    "Content-Type": "application/json"
}

prov = RappiSessionProvider()
if prov.context and prov.context._access_token:
    headers["Authorization"] = f"Bearer {prov.context._access_token}"

def test_url(url, method="POST", payload=None):
    try:
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"Success! {url} -> {resp.getcode()}")
        print(resp.read().decode('utf-8')[:200])
    except Exception as e:
        code = getattr(e, 'code', 'N/A')
        print(f"Fail: {url} -> {code}")

test_url("https://www.rappi.com.mx/api/restaurant/home", "POST", {"lat": LAT, "lng": LNG, "offset": 30, "limit": 30})
test_url("https://www.rappi.com.mx/api/restaurants/home", "POST", {"lat": LAT, "lng": LNG, "offset": 30, "limit": 30})
test_url("https://www.rappi.com.mx/api/restaurant/home", "GET")
test_url("https://www.rappi.com.mx/api/restaurant", "GET")
test_url("https://services.mxgrability.rappi.com/api/web-gateway/web/restaurants-bus/v1/page", "POST", {"lat": LAT, "lng": LNG})
test_url("https://services.mxgrability.rappi.com/api/ms/discovery/v1/restaurants", "POST", {"lat": LAT, "lng": LNG})
