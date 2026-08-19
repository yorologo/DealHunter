import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.historico import analyze_history
from dealhunter.db import get_default_db_path

def main():
    db_path = get_default_db_path()
    config = {}
    res = analyze_history(db_path, config)
    
    distribution = {
        "NEW_LOW": [],
        "REAL_DEAL": [],
        "GOOD_PRICE": [],
        "NORMAL": [],
        "INSUFFICIENT_HISTORY": [],
        "SUSPICIOUS_REFERENCE_PRICE": []
    }
    
    for r in res:
        estado = r["deal_status"]
        if estado in distribution:
            distribution[estado].append(r)
        if "SUSPICIOUS_REFERENCE_PRICE" in r.get("reason", ""):
            distribution["SUSPICIOUS_REFERENCE_PRICE"].append(r)
            
    print("=== DISTRIBUTION ===")
    for k, v in distribution.items():
        print(f"{k}: {len(v)}")
        
    print("\n=== SAMPLES ===")
    for k in ["NEW_LOW", "REAL_DEAL", "GOOD_PRICE", "SUSPICIOUS_REFERENCE_PRICE"]:
        sample = random.sample(distribution[k], min(5, len(distribution[k])))
        print(f"\n--- {k} SAMPLES ---")
        for s in sample:
            print(f"Product: {s['product_name'][:30]}")
            print(f"Store: {s['store_name']}")
            print(f"Price: {s['current_price']}, Min: {s['historical_min']}, Med: {s['median_30d']}")
            print(f"Reason: {s['reason']}")
            print("-" * 20)

if __name__ == '__main__':
    main()
