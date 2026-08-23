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
    "https://services.mxgrability.rappi.com/graphql",
    "https://services.mxgrability.rappi.com/api/graphql",
    "https://www.rappi.com.mx/graphql"
]
for url in endpoints:
    try:
        req = urllib.request.Request(url, data=json.dumps({"query": "{ __typename }"}).encode('utf-8'), headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"POST {url} -> {resp.getcode()}")
    except Exception as e:
        code = getattr(e, 'code', 'N/A')
        print(f"POST {url} -> {code}")
