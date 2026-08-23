import json, math, os
from collections import defaultdict

def percentile(N, percent, key=lambda x:x):
    if not N: return 0
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c: return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1

def main():
    if not os.path.exists("experiments/adaptive_optimization/exp2.json") or not os.path.exists("experiments/adaptive_optimization/exp3.json"):
        print("Waiting for data...")
        return
        
    with open("experiments/adaptive_optimization/exp2.json") as f:
        exp2 = json.load(f)
    with open("experiments/adaptive_optimization/exp3.json") as f:
        exp3 = json.load(f)
        
    # Build maps
    e2_q_ids = {r["query"]: set(r["ids"]) for r in exp2}
    e3_q_ids = {r["query"]: set(r["ids"]) for r in exp3}
    
    e2_univ = set()
    for ids in e2_q_ids.values(): e2_univ.update(ids)
    
    e3_univ = set()
    for ids in e3_q_ids.values(): e3_univ.update(ids)
    
    # 6. MÉTRICAS OUT-OF-SAMPLE
    fases = defaultdict(list)
    for r in exp3:
        fases[r["fase"]].append(r["query"])
        
    s27_q = fases["A"]
    s37_q = s27_q + fases["B"]
    s44_q = s37_q + fases["C"]
    s53_q = s44_q + fases["D"]
    s57_q = s53_q + fases["E"]
    hybrid_q = s57_q + fases["F"]
    full_q = hybrid_q + fases["G"]
    
    def eval_set(q_list):
        stores = set()
        for q in q_list:
            stores.update(e3_q_ids.get(q, set()))
        return stores
        
    e3_full = eval_set(full_q)
    
    def print_set_metrics(name, q_list):
        stores = eval_set(q_list)
        cov = len(stores)/len(e3_full) if e3_full else 0
        missing = len(e3_full - stores)
        print(f"--- {name} ---")
        print(f"requests: {len(q_list)}")
        print(f"merchants: {len(stores)}")
        print(f"coverage: {cov*100:.2f}%")
        print(f"missing: {missing}")
        return stores
        
    print("=== OUT-OF-SAMPLE ===")
    print_set_metrics("S27", s27_q)
    print_set_metrics("S37", s37_q)
    print_set_metrics("S44", s44_q)
    print_set_metrics("S53", s53_q)
    s57_stores = print_set_metrics("S57", s57_q)
    hybrid_stores = print_set_metrics("HYBRID", hybrid_q)
    print_set_metrics("FULL", full_q)
    
    # 7. RESIDUAL CRÍTICO
    print("\n=== RESIDUAL CRÍTICO (missed by HYBRID) ===")
    missed_by_hybrid = e3_full - hybrid_stores
    print(f"merchants missed by HYBRID: {len(missed_by_hybrid)}")
    
    # Find which queries found them in EXP3
    store_to_e3q = defaultdict(list)
    for q in full_q:
        for sid in e3_q_ids.get(q, []):
            store_to_e3q[sid].append(q)
            
    for sid in missed_by_hybrid:
        queries = store_to_e3q[sid]
        exclusive = len(queries) == 1
        in_exp2 = sid in e2_univ
        print(f"  Merchant: {sid}")
        print(f"  Queries: {queries} (depths: {[len(q) for q in queries]})")
        print(f"  Exclusive: {exclusive}")
        print(f"  in EXP2: {in_exp2}")
        
    # 8. GENERALIZACIÓN DE LAS 57 QUERIES (QUERY STABILITY)
    print("\n=== QUERY STABILITY (S57) ===")
    stable_prod = 0
    degraded = 0
    newly_useful = 0
    jaccards = []
    
    # Productive = provided new merchants in sequential run. 
    # But for a specific query, "useful" could just mean len(ids) > 0 or it found exclusive.
    # We will just compare sets.
    for q in s57_q:
        e2_st = e2_q_ids.get(q, set())
        e3_st = e3_q_ids.get(q, set())
        intersection = e2_st.intersection(e3_st)
        union = e2_st.union(e3_st)
        jaccard = len(intersection) / len(union) if union else 0
        jaccards.append(jaccard)
        
        if len(e2_st) > 0 and len(e3_st) > 0:
            stable_prod += 1
        elif len(e2_st) > 0 and len(e3_st) == 0:
            degraded += 1
        elif len(e2_st) == 0 and len(e3_st) > 0:
            newly_useful += 1
            
    print(f"stable productive queries: {stable_prod}")
    print(f"degraded queries: {degraded}")
    print(f"newly useful queries: {newly_useful}")
    print(f"average query-set Jaccard: {sum(jaccards)/len(jaccards):.2f}" if jaccards else 0)
    
    # 9. MERCHANT GENERALIZATION
    print("\n=== TEMPORAL STABILITY (MERCHANTS) ===")
    overlap = e2_univ.intersection(e3_univ)
    jaccard_univ = len(overlap) / len(e2_univ.union(e3_univ)) if e2_univ.union(e3_univ) else 0
    print(f"EXP2 merchants: {len(e2_univ)}")
    print(f"EXP3 merchants: {len(e3_univ)}")
    print(f"overlap: {len(overlap)}")
    print(f"EXP2-only: {len(e2_univ - e3_univ)}")
    print(f"EXP3-only: {len(e3_univ - e2_univ)}")
    print(f"Jaccard: {jaccard_univ:.2f}")
    
    # 10. THRESHOLD SWEEP OFFLINE
    print("\n=== THRESHOLD SWEEP (on EXP3 data) ===")
    # Re-simulate the adaptive tree for EXP3 with different thresholds
    def simulate_adaptive(threshold):
        expanded = set()
        reqs = 0
        stores = set()
        
        # Depth 1
        for c in "abcdefghijklmnopqrstuvwxyz":
            q = c
            reqs += 1
            st = e3_q_ids.get(q, set())
            stores.update(st)
            
            raw = next((r["raw"] for r in exp3 if r["query"] == q), 0)
            if raw >= threshold:
                expanded.add(q)
                # Depth 2
                for c2 in "abcdefghijklmnopqrstuvwxyz":
                    q2 = q + c2
                    reqs += 1
                    st2 = e3_q_ids.get(q2, set())
                    stores.update(st2)
                    
        return reqs, stores
        
    for thr in [30, 35, 40, 45, 50, 55, 60]:
        reqs, stores = simulate_adaptive(thr)
        cov = len(stores)/len(e3_full) if e3_full else 0
        print(f"threshold {thr} | requests: {reqs} | merchants: {len(stores)} | coverage: {cov*100:.2f}%")
        
    # 11. CAP ANALYSIS
    print("\n=== CAP ANALYSIS (Depth 1 in EXP3) ===")
    d1_raws = sorted([r["raw"] for r in exp3 if len(r["query"]) == 1])
    if d1_raws:
        print(f"min: {d1_raws[0]}")
        print(f"median: {percentile(d1_raws, 0.5)}")
        print(f"P90: {percentile(d1_raws, 0.90)}")
        print(f"P95: {percentile(d1_raws, 0.95)}")
        print(f"max: {d1_raws[-1]}")
    
        if max(d1_raws) == d1_raws[-1] and d1_raws.count(max(d1_raws)) > 3:
            print("cap classification: FIXED_CAP")
        else:
            print("cap classification: VARIABLE_CAP")
            
    print("\nDECISION LOGIC PREP:")
    h_cov = len(hybrid_stores)/len(e3_full) if e3_full else 0
    if h_cov >= 0.99 and len(hybrid_q) <= 100:
        print("DECISION: HYBRID_VALIDATED")
    elif h_cov >= 0.95:
        print("DECISION: HYBRID_NEEDS_RESIDUAL")
    else:
        print("DECISION: SET_COVER_OVERFIT")

if __name__ == "__main__":
    main()
