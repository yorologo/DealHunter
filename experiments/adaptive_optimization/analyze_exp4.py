import json, math, os
from collections import defaultdict

def percentile_val(N, percent):
    if not N: return 0
    # To get "top 20%", we want the 80th percentile value.
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c: return N[int(k)]
    d0 = N[int(f)] * (c-k)
    d1 = N[int(c)] * (k-f)
    return d0+d1

def pareto_frontier(points):
    # points = [(requests, coverage, name), ...]
    # we want to MINIMIZE requests and MAXIMIZE coverage
    # so we sort by requests ascending.
    points_sorted = sorted(points, key=lambda x: x[0])
    frontier = []
    max_cov = -1
    for req, cov, name in points_sorted:
        if cov > max_cov:
            frontier.append((req, cov, name))
            max_cov = cov
    return frontier

def main():
    with open("experiments/adaptive_optimization/exp4_full.json") as f:
        logs = json.load(f)
        
    # Build maps
    q_ids = {r["query"]: set(r["ids"]) for r in logs}
    d1_logs = [r for r in logs if len(r["query"]) == 1]
    
    # Calculate FULL reference (all 702 queries)
    full_stores = set()
    for ids in q_ids.values(): full_stores.update(ids)
    full_count = len(full_stores)
    
    # Helper to simulate a policy
    def simulate_policy(expanded_letters):
        reqs = 26 # depth 1
        stores = set()
        for r in d1_logs:
            stores.update(r["ids"])
            
        for l in expanded_letters:
            for c in "abcdefghijklmnopqrstuvwxyz":
                q2 = l + c
                reqs += 1
                stores.update(q_ids.get(q2, set()))
                
        cov = len(stores)/full_count if full_count else 0
        missing = full_count - len(stores)
        return reqs, len(stores), cov, missing

    print("=== FIXED THRESHOLD ===")
    fixed_results = []
    for t in [30, 32, 34, 35, 36, 38, 40, 42, 43, 44, 45, 46, 47, 48, 50]:
        expanded = [r["query"] for r in d1_logs if r["raw"] >= t]
        reqs, st, cov, missing = simulate_policy(expanded)
        fixed_results.append((reqs, cov, f"Fixed {t}"))
        print(f"{t} | {reqs} | {cov*100:.2f}% | {cov*100:.2f}% | {missing}")
        
    print("\n=== TOP-K ===")
    # Sort depth 1 by raw count descending
    d1_sorted = sorted(d1_logs, key=lambda x: x["raw"], reverse=True)
    topk_results = []
    for k in [4, 6, 8, 10, 12, 15, 18, 20, 24]:
        expanded = [r["query"] for r in d1_sorted[:k]]
        reqs, st, cov, missing = simulate_policy(expanded)
        topk_results.append((reqs, cov, f"Top-K {k}"))
        print(f"{k} | {reqs} | {cov*100:.2f}% | {cov*100:.2f}% | {missing}")
        
    print("\n=== PERCENTILE ===")
    d1_raws = sorted([r["raw"] for r in d1_logs])
    pct_results = []
    for pct, name in [(0.8, "Top 20%"), (0.75, "Top 25%"), (0.7, "Top 30%"), (0.6, "Top 40%"), (0.5, "Top 50%")]:
        thr = percentile_val(d1_raws, pct)
        expanded = [r["query"] for r in d1_logs if r["raw"] >= thr]
        reqs, st, cov, missing = simulate_policy(expanded)
        pct_results.append((reqs, cov, f"Percentile {name} (thr={thr:.1f})"))
        print(f"{name} | {reqs} | {cov*100:.2f}% | {cov*100:.2f}% | {missing}")

    print("\n=== CHILD GAIN ANALYSIS ===")
    ranges = {"<30": [], "30-34": [], "35-39": [], "40-44": [], "45-49": [], "50-54": [], "55+": []}
    
    parent_raws = []
    child_gains = []
    
    for r in d1_logs:
        raw = r["raw"]
        q = r["query"]
        
        # Calculate stores obtained without this parent's children
        # Basically, depth 1 stores + ALL OTHER parents' children stores (assuming they were all expanded)
        # Wait, the prompt says: "merchants obtenidos sin esos children."
        # A simpler way: unique stores in child that are NOT in Depth 1.
        
        # Let's define "without those children":
        # we take the base set = ALL Depth 1.
        base_set = set()
        for d1 in d1_logs: base_set.update(d1["ids"])
        
        child_stores = set()
        for c in "abcdefghijklmnopqrstuvwxyz":
            child_stores.update(q_ids.get(q+c, set()))
            
        additional = len(child_stores - base_set)
        
        parent_raws.append(raw)
        child_gains.append(additional)
        
        if raw < 30: ranges["<30"].append((q, raw, additional))
        elif raw < 35: ranges["30-34"].append((q, raw, additional))
        elif raw < 40: ranges["35-39"].append((q, raw, additional))
        elif raw < 45: ranges["40-44"].append((q, raw, additional))
        elif raw < 50: ranges["45-49"].append((q, raw, additional))
        elif raw < 55: ranges["50-54"].append((q, raw, additional))
        else: ranges["55+"].append((q, raw, additional))
        
    for k, v in ranges.items():
        if not v: continue
        parents = len(v)
        reqs = parents * 26
        add_merchants = sum([x[2] for x in v])
        eff = add_merchants / reqs if reqs else 0
        print(f"{k}: parents={parents}, child_reqs={reqs}, additional={add_merchants}, eff={eff:.2f}")

    # Correlation
    mean_x = sum(parent_raws) / len(parent_raws)
    mean_y = sum(child_gains) / len(child_gains)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(parent_raws, child_gains))
    den = math.sqrt(sum((x - mean_x)**2 for x in parent_raws)) * math.sqrt(sum((y - mean_y)**2 for y in child_gains))
    corr = num / den if den else 0
    print(f"\nCorrelation (Pearson): {corr:.3f}")
    
    print("\n=== PARETO FRONTIER ===")
    all_points = fixed_results + topk_results + pct_results
    frontier = pareto_frontier(all_points)
    for req, cov, name in frontier:
        print(f"{name}: req={req}, cov={cov*100:.2f}%")

    print("\n=== MODES ===")
    normal_cand = [p for p in frontier if p[1] >= 0.97 and p[0] <= 350] # 50% reduction from 702 is ~350
    deep_cand = [p for p in frontier if p[1] >= 0.99]
    
    if normal_cand:
        best_norm = normal_cand[0] # lowest requests
        print(f"NORMAL: {best_norm[2]} ({best_norm[0]} reqs, {best_norm[1]*100:.2f}%)")
    else:
        print("NORMAL: NONE")
        
    if deep_cand:
        best_deep = deep_cand[0]
        print(f"DEEP: {best_deep[2]} ({best_deep[0]} reqs, {best_deep[1]*100:.2f}%)")
    else:
        print("DEEP: NONE")

if __name__ == "__main__":
    main()
