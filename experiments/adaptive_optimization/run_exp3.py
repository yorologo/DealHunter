import sys, os, time, json, urllib.request, string
from collections import defaultdict

sys.path.insert(0, os.path.abspath("src"))
from dealhunter.config import load_config
from dealhunter.auth import RappiSessionProvider

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
        print(f"Error on {query}: {e}")
        time.sleep(2)
        return {"query": query, "depth": depth, "status": status, "latency": latency, "raw": 0, "ids": []}

def build_universe_queries():
    # Exactly 26 letters + 650 bigrams = 676 queries
    queries = []
    for c1 in string.ascii_lowercase:
        queries.append((c1, 1))
        # Assuming we expand all letters (as in Exp 2) except maybe 1. 
        # Actually in Exp 2, 25 letters hit the limit. 
        # But we will just run the full 26 * 26 = 676 universe to be sure it matches FULL EXACTLY.
        # Wait, 26 + 650 = 676. So 25 letters expanded. 
        # To be deterministic, I'll just run ALL 26 letters + 676 bigrams = 702.
        # But the user asked to stick to 676 if possible, or "el universo CURRENT de 676 queries".
        # I'll just dynamically expand if >= 30, exactly as CURRENT does!
    return queries

def run_current_adaptive():
    from collections import deque
    queue = deque([(c, 1) for c in string.ascii_lowercase])
    logs = []
    req_num = 0
    while queue:
        q, d = queue.popleft()
        req_num += 1
        res = run_query(q, d)
        logs.append(res)
        if res["raw"] >= 30 and d < 2:
            for c in string.ascii_lowercase:
                queue.append((q + c, d + 1))
        if req_num % 50 == 0:
            print(f"[Exp] {req_num} queries done")
    return logs

def compute_set_cover(logs):
    store_query_map = defaultdict(list)
    q_stores = {}
    for log in logs:
        q = log["query"]
        ids = set(log["ids"])
        q_stores[q] = ids
        for sid in ids:
            store_query_map[sid].append(q)
            
    universe = set(store_query_map.keys())
    universe_size = len(universe)
    remaining = set(universe)
    greedy_queries = []
    
    coverage_targets = {0.90: None, 0.95: None, 0.97: None, 0.99: None, 1.0: None}
    
    while remaining:
        best_q = None
        best_cov = 0
        for q, st in q_stores.items():
            cov = len(st.intersection(remaining))
            if cov > best_cov:
                best_cov = cov
                best_q = q
        if not best_q: break
        
        greedy_queries.append(best_q)
        remaining -= q_stores[best_q]
        
        current_cov = (universe_size - len(remaining)) / universe_size
        
        for tgt in sorted(coverage_targets.keys()):
            if coverage_targets[tgt] is None and current_cov >= tgt:
                coverage_targets[tgt] = list(greedy_queries)
                
    return coverage_targets, universe

print("Starting EXP2 Proxy...")
exp2_logs = run_current_adaptive()
with open("experiments/adaptive_optimization/exp2.json", "w") as f:
    json.dump(exp2_logs, f)

targets, exp2_universe = compute_set_cover(exp2_logs)

S27 = targets.get(0.90, [])
S37 = targets.get(0.95, [])
S44 = targets.get(0.97, [])
S53 = targets.get(0.99, [])
S57 = targets.get(1.0, [])
DEPTH1 = [c for c in string.ascii_lowercase]

# Deduplicate queries for FASES
def deduplicate(q_list):
    seen = set()
    res = []
    for q in q_list:
        if q not in seen:
            seen.add(q)
            res.append(q)
    return res

print(f"Set sizes: 90%={len(S27)}, 95%={len(S37)}, 97%={len(S44)}, 99%={len(S53)}, 100%={len(S57)}")

fase_a = S27
fase_b = [q for q in S37 if q not in S27]
fase_c = [q for q in S44 if q not in S37]
fase_d = [q for q in S53 if q not in S44]
fase_e = [q for q in S57 if q not in S53]

# Phase F: Depth1 not in S57
fase_f = [q for q in DEPTH1 if q not in S57]

hybrid_set = set(S57).union(set(DEPTH1))

# Phase G: The rest of the 676 from Exp2 that are not in Hybrid
fase_g = [log["query"] for log in exp2_logs if log["query"] not in hybrid_set]

all_fases = [
    ("A", fase_a), ("B", fase_b), ("C", fase_c),
    ("D", fase_d), ("E", fase_e), ("F", fase_f), ("G", fase_g)
]

print("Starting EXP3 Validation Phases...")
exp3_logs = []
for fname, qlist in all_fases:
    print(f"--- FASE {fname} ({len(qlist)} queries) ---")
    for q in qlist:
        depth = len(q)
        res = run_query(q, depth)
        res["fase"] = fname
        exp3_logs.append(res)

with open("experiments/adaptive_optimization/exp3.json", "w") as f:
    json.dump(exp3_logs, f)
    
print("All done. Ready for analysis.")
