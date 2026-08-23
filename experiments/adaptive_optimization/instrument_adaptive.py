import sys, os, time, json, urllib.request, string
from collections import deque
sys.path.insert(0, os.path.abspath("src"))
from dealhunter.config import load_config
from dealhunter.auth import RappiSessionProvider

def run_instrumented():
    cfg = load_config()
    lat = cfg.get('lat')
    lng = cfg.get('lng')
    if not lat or not lng:
        print("Error: Missing lat/lng in config.toml")
        sys.exit(1)
        
    print(f"Running Adaptive Discovery at {lat}, {lng}")
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
        
    queue = deque([(c, 1) for c in string.ascii_lowercase])
    MAX_DEPTH = 2
    LIMIT_THRESHOLD = 30
    
    unique_stores_total = set()
    logs = []
    
    req_num = 0
    start_total = time.time()
    
    try:
        while queue:
            query, depth = queue.popleft()
            req_num += 1
            payload = json.dumps({"query": query, "lat": lat, "lng": lng, "limit": 100}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    latency = time.time() - t0
                    stores = data.get("stores", [])
                    raw_count = len(stores)
                    
                    returned_ids = []
                    new_ids = []
                    
                    for s in stores:
                        sid = str(s.get("store_id"))
                        returned_ids.append(sid)
                        if sid not in unique_stores_total:
                            new_ids.append(sid)
                            unique_stores_total.add(sid)
                            
                    is_saturated = raw_count >= LIMIT_THRESHOLD
                    
                    logs.append({
                        "req_num": req_num,
                        "query": query,
                        "length": len(query),
                        "depth": depth,
                        "status": 200,
                        "latency": latency,
                        "raw_merchants": raw_count,
                        "unique_returned": len(set(returned_ids)),
                        "new_merchants": len(new_ids),
                        "cumulative": len(unique_stores_total),
                        "saturated": is_saturated,
                        "returned_ids": returned_ids,
                        "new_ids": new_ids
                    })
                    
                    if is_saturated and depth < MAX_DEPTH:
                        for c in string.ascii_lowercase:
                            queue.append((query + c, depth + 1))
                            
            except Exception as e:
                latency = time.time() - t0
                status = getattr(e, 'code', 0)
                logs.append({
                    "req_num": req_num,
                    "query": query,
                    "length": len(query),
                    "depth": depth,
                    "status": status,
                    "latency": latency,
                    "error": str(e),
                    "raw_merchants": 0,
                    "unique_returned": 0,
                    "new_merchants": 0,
                    "cumulative": len(unique_stores_total),
                    "saturated": False,
                    "returned_ids": [],
                    "new_ids": []
                })
                print(f"Error on {query}: {e}")
                time.sleep(2) # Backoff
            
            if req_num % 50 == 0:
                print(f"[{req_num}] Query '{query}', Raw: {logs[-1]['raw_merchants']}, New: {logs[-1]['new_merchants']}, Cumul: {len(unique_stores_total)}")
                
    except KeyboardInterrupt:
        print("Interrupted by user.")
        
    duration = time.time() - start_total
    
    with open("experiments/adaptive_optimization/adaptive_results.json", "w") as f:
        json.dump({
            "lat": lat,
            "lng": lng,
            "duration": duration,
            "total_requests": req_num,
            "unique_merchants": len(unique_stores_total),
            "logs": logs
        }, f, indent=2)
        
    print(f"Done! Requests: {req_num}, Unique: {len(unique_stores_total)}, Duration: {duration:.2f}s")

if __name__ == "__main__":
    run_instrumented()
