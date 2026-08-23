import sys, os, time, json, urllib.request, string, math
from collections import defaultdict

sys.path.insert(0, os.path.abspath("src"))
from dealhunter.config import load_config
from dealhunter.auth import RappiSessionProvider

def notify(mode, msg):
    os.system(f"$HOME/bin/ai-notify {mode} '{msg}'")

cfg = load_config()
lat = cfg.get('lat')
lng = cfg.get('lng')

url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
prov = RappiSessionProvider()
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.rappi.com.mx"
}
if prov.context and prov.context._access_token:
    headers["Authorization"] = f"Bearer {prov.context._access_token}"

def run_query(query, depth):
    payload = json.dumps({"query": query, "lat": lat, "lng": lng, "limit": 100}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            latency = time.time() - t0
            stores = data.get("stores", [])
            raw_count = len(stores)
            ids = [str(s.get("store_id")) for s in stores]
            return {"query": query, "depth": depth, "status": 200, "latency": latency, "raw": raw_count, "ids": ids}
    except Exception as e:
        latency = time.time() - t0
        status = getattr(e, 'code', 0)
        time.sleep(2)
        return {"query": query, "depth": depth, "status": status, "latency": latency, "raw": 0, "ids": []}

def gather_data():
    notify("info", "Crawler V2: medición de discovery iniciada")
    logs = []
    # Run depth 1
    d1_queries = list(string.ascii_lowercase)
    # Run depth 2 for ALL depth 1 to allow simulating ANY policy offline
    d2_queries = [c1 + c2 for c1 in string.ascii_lowercase for c2 in string.ascii_lowercase]
    
    all_queries = d1_queries + d2_queries
    
    for i, q in enumerate(all_queries):
        depth = len(q)
        res = run_query(q, depth)
        logs.append(res)
        if (i+1) % 50 == 0:
            print(f"Captured {i+1}/{len(all_queries)} queries")
            
    with open("experiments/adaptive_optimization/exp4_full.json", "w") as f:
        json.dump(logs, f)
        
    notify("info", "Crawler V2: discovery terminado; analizando resultados")
    return logs

if __name__ == "__main__":
    if not os.path.exists("experiments/adaptive_optimization/exp4_full.json"):
        gather_data()
    else:
        print("Data already exists.")
