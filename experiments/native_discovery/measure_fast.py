import sys, os; sys.path.insert(0, os.path.abspath("src"))
import asyncio, json, time, urllib.request, re, sqlite3
from dealhunter.config import load_config
from dealhunter.auth import RappiSessionProvider

cfg = load_config()
LAT = cfg.get('lat', 19.432608)
LNG = cfg.get('lng', -99.133209)

def get_same_zone_stores():
    conn = sqlite3.connect('rappi-deals.db')
    c = conn.cursor()
    c.execute('''
        SELECT DISTINCT store_id 
        FROM observations 
        WHERE run_id IN (SELECT run_id FROM runs WHERE abs(lat - ?) < 0.01 AND abs(lng - ?) < 0.01)
    ''', (LAT, LNG))
    stores = set(str(row[0]) for row in c.fetchall())
    conn.close()
    return stores

known_stores = get_same_zone_stores()

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

def main():
    print(f"EXPERIMENT_ZONE: {LAT}, {LNG}")
    print(f"REFERENCE_STORE_IDS (same zone): {len(known_stores)}")
    
    ssr_res = measure_ssr_web()
    uni_res = measure_unified_star()
    
    results = [ssr_res, uni_res]
    
    for r in results:
        found = r["stores"]
        known_recovered = found.intersection(known_stores)
        new_merchants = found - known_stores
        cov = (len(known_recovered) / len(known_stores)) * 100 if len(known_stores) > 0 else 0
        print(f"--- {r['name']} ---")
        print(f"Unique Merchants: {len(found)}")
        print(f"Overlap with REF: {len(known_recovered)}")
        print(f"Native-Only (New): {len(new_merchants)}")
        print(f"Coverage: {cov:.2f}%")
        print(f"Requests: {r['reqs']}")
        print(f"Duration: {r['duration']:.2f}s")
        print()

if __name__ == "__main__":
    main()
