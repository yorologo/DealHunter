import sys, os; sys.path.insert(0, os.path.abspath("src"))
import asyncio, json, time, urllib.request, re, sqlite3
from dealhunter.auth import RappiSessionProvider
from dealhunter.catalog_sync import CoverageReport

LAT = 19.432608
LNG = -99.133209
try:
    from dealhunter.config import load_config
    cfg = load_config()
    LAT = cfg.get('lat', LAT)
    LNG = cfg.get('lng', LNG)
except Exception:
    pass

def get_known_stores():
    conn = sqlite3.connect('rappi-deals.db')
    c = conn.cursor()
    c.execute("SELECT store_id, type FROM stores")
    stores = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return stores

known_stores = get_known_stores()

def measure_ssr_web():
    start = time.time()
    url = f"https://www.rappi.com.mx/restaurantes?csr=false&lat={LAT}&lng={LNG}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    stores = set()
    req_count = 0
    try:
        req_count += 1
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        m = re.search(r'<script id=\"__NEXT_DATA__\" type=\"application/json\">(.*?)</script>', html)
        if m:
            d = json.loads(m.group(1))
            cat = d.get('props', {}).get('pageProps', {}).get('catalog', {})
            for r in cat.get('restaurants', []):
                stores.add(str(r.get('id')))
    except Exception as e:
        print("SSR error:", e)
    return {"name": "Web SSR /restaurantes", "duration": time.time() - start, "reqs": req_count, "stores": stores}

def measure_unified_star():
    start = time.time()
    prov = RappiSessionProvider()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.rappi.com.mx"
    }
    if prov.context and prov.context._access_token:
        headers["Authorization"] = f"Bearer {prov.context._access_token}"
    
    url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
    payload = {"lat": LAT, "lng": LNG, "query": "*", "limit": 100}
    stores = set()
    req_count = 0
    try:
        req_count += 1
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method='POST')
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        for s in data.get('stores', []):
            stores.add(str(s.get('store_id')))
    except Exception as e:
        print("Unified * error:", e)
    return {"name": "Unified Search (*)", "duration": time.time() - start, "reqs": req_count, "stores": stores}

async def measure_adaptive():
    from dealhunter.catalog_sync import MerchantDiscovery, AuthenticatedHttpClient
    prov = RappiSessionProvider()
    client = AuthenticatedHttpClient(prov)
    disc = MerchantDiscovery(client)
    report = CoverageReport()
    
    start = time.time()
    merchants = await disc.discover_merchants(LAT, LNG, report)
    stores = set([str(m['store_id']) for m in merchants])
    
    return {"name": "Adaptive Search (Current)", "duration": time.time() - start, "reqs": report.authenticated_requests, "stores": stores}

async def main():
    print(f"Total Known Stores (baseline): {len(known_stores)}")
    
    ssr_res = measure_ssr_web()
    uni_res = measure_unified_star()
    ada_res = await measure_adaptive()
    
    results = [ssr_res, uni_res]
    
    # Union of native sources
    native_union_stores = ssr_res["stores"].union(uni_res["stores"])
    native_reqs = ssr_res["reqs"] + uni_res["reqs"]
    
    # Compare against known
    for r in results:
        found = r["stores"]
        known_recovered = found.intersection(known_stores.keys())
        new_merchants = found - known_stores.keys()
        cov = (len(known_recovered) / len(known_stores)) * 100 if len(known_stores) > 0 else 0
        print(f"--- {r['name']} ---")
        print(f"Requests: {r['reqs']}")
        print(f"Unique Merchants: {len(found)}")
        print(f"Known Recovered: {len(known_recovered)}")
        print(f"New Merchants: {len(new_merchants)}")
        print(f"Coverage: {cov:.2f}%")
        print(f"Duration: {r['duration']:.2f}s")
        print()
    
    print("--- UNION (Native Sources) ---")
    known_rec = native_union_stores.intersection(known_stores.keys())
    new_merch = native_union_stores - known_stores.keys()
    print(f"Unique Merchants: {len(native_union_stores)}")
    print(f"Known Recovered: {len(known_rec)}")
    print(f"New Merchants: {len(new_merch)}")
    print(f"Requests: {native_reqs}")
    print()
    
    print("--- ADAPTIVE SEARCH (Current) ---")
    ada_stores = ada_res["stores"]
    ada_known_rec = ada_stores.intersection(known_stores.keys())
    ada_new_merch = ada_stores - known_stores.keys()
    print(f"Unique Merchants: {len(ada_stores)}")
    print(f"Requests: {ada_res['reqs']}")
    print(f"Known Recovered: {len(ada_known_rec)}")
    print(f"New Merchants: {len(ada_new_merch)}")
    print(f"Duration: {ada_res['duration']:.2f}s")
    if ada_res['reqs'] > 0:
        print(f"Merchants/Request: {len(ada_stores)/ada_res['reqs']:.2f}")
    
    print("--- COMPARISON ---")
    nat_cov = (len(known_rec)/len(known_stores))*100 if known_stores else 0
    ada_cov = (len(ada_known_rec)/len(known_stores))*100 if known_stores else 0
    print(f"Native Coverage: {nat_cov:.2f}%")
    print(f"Adaptive Coverage: {ada_cov:.2f}%")
    
if __name__ == "__main__":
    asyncio.run(main())
