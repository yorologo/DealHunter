import json, math, os
from collections import defaultdict

def main():
    if not os.path.exists("experiments/adaptive_optimization/adaptive_results.json"):
        print("Waiting for results...")
        return
        
    with open("experiments/adaptive_optimization/adaptive_results.json") as f:
        data = json.load(f)
        
    logs = data["logs"]
    
    # 4. INVESTIGAR EL 676
    len_counts = defaultdict(int)
    for log in logs:
        len_counts[log["length"]] += 1
        
    print("=== INVESTIGAR EL 676 ===")
    print(f"Total requests: {data['total_requests']}")
    for l in sorted(len_counts.keys()):
        print(f"Length {l}: {len_counts[l]} queries")
        
    # 5. DISTRIBUCIÓN DE UTILIDAD
    # Wait, new_merchants in the logs is sensitive to the ORDER of queries (cumulative).
    # A better utility metric is "If I ran this query, how many unique merchants does it return?".
    # But wait, "Duplicate-only" means a query where ALL its merchants were found by prior queries?
    # Actually, let's recalculate utility properly, or use the order-dependent one to see wasted work in CURRENT.
    
    buckets = {"0": 0, "1": 0, "2-4": 0, "5-9": 0, "10-19": 0, "20+": 0, "SATURATED": 0}
    zero_new = 0
    duplicate_only = 0
    productive = 0
    
    for log in logs:
        n = log["new_merchants"]
        is_sat = log["saturated"]
        
        if is_sat:
            buckets["SATURATED"] += 1
        elif n == 0:
            buckets["0"] += 1
        elif n == 1:
            buckets["1"] += 1
        elif 2 <= n <= 4:
            buckets["2-4"] += 1
        elif 5 <= n <= 9:
            buckets["5-9"] += 1
        elif 10 <= n <= 19:
            buckets["10-19"] += 1
        else:
            buckets["20+"] += 1
            
        if n == 0:
            zero_new += 1
            if log["unique_returned"] > 0:
                duplicate_only += 1
        else:
            productive += 1
            
    print("\n=== DISTRIBUCIÓN DE UTILIDAD (Orden Actual) ===")
    print(f"0 nuevos: {zero_new} (Duplicados puros: {duplicate_only})")
    print(f"Productivas: {productive}")
    print(f"Desperdicio: {(zero_new / len(logs))*100:.2f}%")
    print("Buckets:")
    for k, v in buckets.items():
        print(f"  {k}: {v}")

    # 6. EXCLUSIVE CONTRIBUTION
    store_query_map = defaultdict(list)
    for log in logs:
        for sid in set(log["returned_ids"]):
            store_query_map[sid].append(log["query"])
            
    exclusive_counts = defaultdict(int)
    for sid, queries in store_query_map.items():
        if len(queries) == 1:
            exclusive_counts[queries[0]] += 1
            
    # Print some examples
    print("\n=== EXCLUSIVE CONTRIBUTION ===")
    excl_queries = sorted([(q, count) for q, count in exclusive_counts.items()], key=lambda x: -x[1])
    print(f"Queries with exclusive merchants: {len(excl_queries)}")
    print(f"Top 5 exclusive contributors: {excl_queries[:5]}")
    
    # 7. ¿REALMENTE ES UN TRIE?
    print("\n=== ¿REALMENTE ES UN TRIE? ===")
    # Find a parent that was saturated
    parent_q = None
    for log in logs:
        if log["depth"] == 1 and log["saturated"]:
            parent_q = log["query"]
            break
            
    if parent_q:
        parent_log = next(l for l in logs if l["query"] == parent_q)
        parent_stores = set(parent_log["returned_ids"])
        
        # get all child stores
        child_stores = set()
        for log in logs:
            if log["query"].startswith(parent_q) and len(log["query"]) == len(parent_q) + 1:
                child_stores.update(log["returned_ids"])
                
        intersection = parent_stores.intersection(child_stores)
        union_set = parent_stores.union(child_stores)
        jaccard = len(intersection) / len(union_set) if union_set else 0
        
        print(f"Parent '{parent_q}': {len(parent_stores)} stores")
        print(f"Children '{parent_q}*': {len(child_stores)} total unique stores")
        print(f"Intersection: {len(intersection)}")
        print(f"Child ⊆ Parent: {child_stores.issubset(parent_stores)}")
        print(f"Parent ⊆ Child: {parent_stores.issubset(child_stores)}")
        print(f"Jaccard: {jaccard:.2f}")
        
    # 8. SATURATION & 9. PROFUNDIDAD
    depth_merchants = defaultdict(set)
    for log in logs:
        depth_merchants[log["depth"]].update(log["returned_ids"])
        
    print("\n=== PROFUNDIDAD ===")
    d1 = depth_merchants[1]
    d2 = depth_merchants[2]
    print(f"Depth 1 total unique: {len(d1)}")
    print(f"Depth 2 total unique: {len(d2)}")
    print(f"Marginal gain (Depth 2 not in Depth 1): {len(d2 - d1)}")
    
    # 10. SET COVER OFFLINE
    print("\n=== SET COVER OFFLINE & SIMULATION ===")
    universe = set(store_query_map.keys())
    universe_size = len(universe)
    
    remaining = set(universe)
    greedy_queries = []
    
    # precompute query -> stores set
    q_stores = {log["query"]: set(log["returned_ids"]) for log in logs}
    
    coverage_targets = [0.9, 0.95, 0.97, 0.99, 1.0]
    target_idx = 0
    
    while remaining and target_idx < len(coverage_targets):
        best_q = None
        best_cov = 0
        
        for q, st in q_stores.items():
            cov = len(st.intersection(remaining))
            if cov > best_cov:
                best_cov = cov
                best_q = q
                
        if not best_q:
            break
            
        greedy_queries.append(best_q)
        remaining -= q_stores[best_q]
        
        current_cov = (universe_size - len(remaining)) / universe_size
        while target_idx < len(coverage_targets) and current_cov >= coverage_targets[target_idx]:
            print(f"Coverage {coverage_targets[target_idx]*100:.0f}%: {len(greedy_queries)} queries ({(1 - len(greedy_queries)/len(logs))*100:.2f}% reduction)")
            target_idx += 1
            
    # Simulation
    def simulate(query_list):
        seen = set()
        for q in query_list:
            seen.update(q_stores[q])
        lost = universe - seen
        excl_lost = [sid for sid in lost if len(store_query_map[sid]) == 1]
        return len(query_list), len(seen), len(seen)/universe_size, len(lost), len(excl_lost)
        
    print("\n=== SIMULACION ===")
    
    # A. CURRENT
    s_curr = simulate(q_stores.keys())
    print(f"CURRENT: req={s_curr[0]}, cov={s_curr[2]*100:.1f}%, lost={s_curr[3]}, excl_lost={s_curr[4]}")
    
    # B. SATURATION ONLY
    sat_queries = [log["query"] for log in logs if log["depth"] == 1 or (len(log["query"])>1 and logs[len_counts[1]-1]["saturated"])] 
    # Wait, the rule is: expand only if parent was saturated.
    # Our current algorithm ALREADY does exactly this!
    # Let's verify if CURRENT is already SATURATION_ONLY.
    print("CURRENT IS SATURATION_ONLY (as per code).")
    
    # C. GREEDY KNOWN
    s_greedy = simulate(greedy_queries)
    print(f"GREEDY_KNOWN: req={s_greedy[0]}, cov={s_greedy[2]*100:.1f}%, lost={s_greedy[3]}, excl_lost={s_greedy[4]}")
    
if __name__ == "__main__":
    main()
