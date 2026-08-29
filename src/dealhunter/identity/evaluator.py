import sqlite3
import json
from collections import defaultdict
from .normalization import extract_signature, is_hard_reject

def generate_candidates(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Load all products
    c.execute('''
        SELECT provider, store_id, product_id, name, brand, quantity, unit, category
        FROM products
    ''')
    rows = c.fetchall()
    
    products = []
    for r in rows:
        sig = extract_signature(r[4], r[3], r[5], r[6])
        products.append({
            "provider": r[0],
            "store_id": r[1],
            "product_id": r[2],
            "name": r[3],
            "brand": r[4],
            "category": r[7],
            "signature": sig
        })
        
    conn.close()
    
    # 2. Naive Candidate Generation (shadow mode: cross-provider only)
    # Group by normalized base_name token overlap + brand
    candidates = []
    for i, p1 in enumerate(products):
        for j in range(i + 1, len(products)):
            p2 = products[j]
            
            # Shadow rule: Only evaluate cross-provider
            if p1["provider"] == p2["provider"]:
                continue
                
            # Filter candidates by hard reject
            rejected, reason = is_hard_reject(p1["signature"], p2["signature"])
            if rejected:
                continue
                
            # Require brand match or token overlap
            s1_tokens = set(p1["signature"]["base_name"].split())
            s2_tokens = set(p2["signature"]["base_name"].split())
            
            if not s1_tokens or not s2_tokens:
                continue
                
            overlap = len(s1_tokens.intersection(s2_tokens))
            min_len = min(len(s1_tokens), len(s2_tokens))
            
            if min_len > 0 and overlap / min_len >= 0.5:
                candidates.append({
                    "p1": p1,
                    "p2": p2,
                    "confidence": overlap / min_len
                })
                
    return candidates

def evaluate_shadow(db_path):
    candidates = generate_candidates(db_path)
    print(f"Shadow mode generated {len(candidates)} cross-provider candidates.")
    
    # Dump a sample
    if candidates:
        print("\nSample Candidates:")
        for c in sorted(candidates, key=lambda x: x["confidence"], reverse=True)[:10]:
            print(f"- [Score: {c['confidence']:.2f}]")
            print(f"  {c['p1']['provider']}: {c['p1']['name']} (Sig: {c['p1']['signature']})")
            print(f"  {c['p2']['provider']}: {c['p2']['name']} (Sig: {c['p2']['signature']})")
            
    return candidates
