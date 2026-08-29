import sqlite3
import json
from collections import defaultdict
from .normalization import extract_signature, is_hard_reject


def generate_candidates(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT provider, store_id, product_id, name, brand, quantity, unit, category
        FROM products
    ''')
    rows = c.fetchall()
    conn.close()
    
    products_by_provider = defaultdict(list)
    for r in rows:
        sig = extract_signature(r[4], r[3], r[5], r[6])
        p = {
            "provider": r[0],
            "store_id": r[1],
            "product_id": r[2],
            "name": r[3],
            "brand": r[4],
            "category": r[7],
            "signature": sig
        }
        products_by_provider[p["provider"]].append(p)
        
    candidates = []
    providers = list(products_by_provider.keys())
    
    for i in range(len(providers)):
        for j in range(i + 1, len(providers)):
            prov1 = providers[i]
            prov2 = providers[j]
            
            # Build index for prov2
            index = defaultdict(list)
            for idx2, p2 in enumerate(products_by_provider[prov2]):
                brand = p2["signature"]["brand"]
                if brand:
                    index[f"brand:{brand}"].append(idx2)
                
                tokens = p2["signature"]["base_name"].split()
                for t in tokens[:3]:
                    if len(t) > 2:
                        index[f"token:{t}"].append(idx2)
                            
            for p1 in products_by_provider[prov1]:
                brand = p1["signature"]["brand"]
                brand_matches = index.get(f"brand:{brand}", []) if brand else []
                
                token_matches = set()
                tokens = p1["signature"]["base_name"].split()
                for t in tokens[:3]:
                    if len(t) > 2:
                        token_matches.update(index.get(f"token:{t}", []))
                        
                # Prioritize high-information evidence (brand matches)
                block_ordered = list(brand_matches)
                for idx in token_matches:
                    if idx not in block_ordered:
                        block_ordered.append(idx)
                                
                if len(block_ordered) > 100:
                    # Deterministic candidate cap sorting by priority (brand > token)
                    block_ordered = block_ordered[:100]
                    
                for idx2 in block_ordered:
                    p2 = products_by_provider[prov2][idx2]
                    
                    rejected, reason = is_hard_reject(p1["signature"], p2["signature"])
                    if rejected:
                        continue
                        
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

def match_products(p1, p2):
    """
    Given two product dictionaries, returns the matching status and reason.
    Returns: status (AUTO_CONFIRMED, REVIEW_REQUIRED, REJECTED), reason
    """
    from .normalization import extract_signature, is_hard_reject
    # simple extraction since we don't have full structured evidence module in src yet
    sig1 = extract_signature(p1.get("brand", ""), p1.get("name", ""), p1.get("quantity"), p1.get("unit"))
    sig2 = extract_signature(p2.get("brand", ""), p2.get("name", ""), p2.get("quantity"), p2.get("unit"))
    
    rejected, reason = is_hard_reject(sig1, sig2)
    if rejected:
        return "REJECTED", reason
        
    s1_tokens = set(sig1["base_name"].split())
    s2_tokens = set(sig2["base_name"].split())
    
    if not s1_tokens or not s2_tokens:
        return "REVIEW_REQUIRED", "Empty base name"
        
    overlap = len(s1_tokens.intersection(s2_tokens))
    min_len = min(len(s1_tokens), len(s2_tokens))
    max_len = max(len(s1_tokens), len(s2_tokens))
    
    ratio_min = overlap / min_len if min_len > 0 else 0
    ratio_max = overlap / max_len if max_len > 0 else 0
    
    has_brand = bool(sig1["brand"] and sig2["brand"])
    has_size = bool(sig1["total"] and sig2["total"])
    
    # Check if prepared
    def is_prepared(name):
        n = name.lower()
        return any(w in n for w in ["taco", "chilaquiles", "torta", "lonche", "hamburguesa", "pizza", "combo", "menu"])
    
    prep1 = is_prepared(p1.get("name", ""))
    prep2 = is_prepared(p2.get("name", ""))
    
    if sig1.get("approximate_quantity") or sig2.get("approximate_quantity"):
        return "REVIEW_REQUIRED", "Approximate/Variable weight item"
        
    if prep1 or prep2:
        return "REVIEW_REQUIRED", "Prepared or fresh item"
        
    # EXACT EVIDENCE GATE:
    # Requires brand, size, NO fresh/prepared, NO approx weight.
    # AND missing evidence check: ratio_max MUST be 1.0 (exact token parity)
    # Token ratio is NOT an authority for EXACT_PRODUCT by itself, but parity is required.
    if ratio_max == 1.0:
        if has_brand and has_size:
            return "AUTO_CONFIRMED", "Exact match with full evidence parity"
        else:
            return "REVIEW_REQUIRED", "Exact token similarity but missing critical evidence (brand/size)"
        
    if ratio_min >= 0.8:
        return "REVIEW_REQUIRED", "High overlap, missing evidence/parity"
        
    if ratio_min >= 0.5:
        return "REVIEW_REQUIRED", "Moderate overlap"
        
    return "REJECTED", "Low overlap"
