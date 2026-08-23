import json, math, os
from collections import defaultdict

def main():
    with open("experiments/adaptive_optimization/adaptive_results.json") as f:
        data = json.load(f)
    logs = data["logs"]
    
    buckets = {"0": 0, "1": 0, "2-4": 0, "5-9": 0, "10-19": 0, "20+": 0}
    saturated_count = 0
    zero_new = 0
    duplicate_only = 0
    productive = 0
    
    for log in logs:
        n = log["new_merchants"]
        is_sat = log["saturated"]
        
        if is_sat:
            saturated_count += 1
            
        if n == 0:
            buckets["0"] += 1
            zero_new += 1
            if log["unique_returned"] > 0:
                duplicate_only += 1
        elif n == 1:
            buckets["1"] += 1
            productive += 1
        elif 2 <= n <= 4:
            buckets["2-4"] += 1
            productive += 1
        elif 5 <= n <= 9:
            buckets["5-9"] += 1
            productive += 1
        elif 10 <= n <= 19:
            buckets["10-19"] += 1
            productive += 1
        else:
            buckets["20+"] += 1
            productive += 1
            
    print("\n=== DISTRIBUCIÓN DE UTILIDAD (Buckets reales) ===")
    print(f"Saturadas: {saturated_count}")
    print(f"0 nuevos: {zero_new} (Duplicados puros: {duplicate_only})")
    print(f"Productivas: {productive}")
    print("Buckets de aportación:")
    for k, v in buckets.items():
        print(f"  {k}: {v}")
if __name__ == "__main__":
    main()
