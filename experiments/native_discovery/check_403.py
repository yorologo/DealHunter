import sys, os; sys.path.insert(0, os.path.abspath("src"))
import urllib.request, json
from dealhunter.auth import RappiSessionProvider

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Origin": "https://www.rappi.com.mx"
}
prov = RappiSessionProvider()
if prov.context and prov.context._access_token:
    headers["Authorization"] = f"Bearer {prov.context._access_token}"

url = "https://www.rappi.com.mx/api/restaurant/home"
req = urllib.request.Request(url, data=json.dumps({}).encode('utf-8'), headers=headers, method="POST")
try:
    resp = urllib.request.urlopen(req)
    print("200 OK")
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8')[:500])
