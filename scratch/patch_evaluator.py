import re

with open('src/dealhunter/identity/evaluator.py', 'r') as f:
    content = f.read()

new_gen = """
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
                block = set()
                brand = p1["signature"]["brand"]
                if brand:
                    block.update(index.get(f"brand:{brand}", []))
                
                tokens = p1["signature"]["base_name"].split()
                for t in tokens[:3]:
                    if len(t) > 2:
                        block.update(index.get(f"token:{t}", []))
                                
                if len(block) > 100:
                    block = list(block)[:100]
                    
                for idx2 in block:
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
"""

# Replace
import re
content = re.sub(r'def generate_candidates\(db_path\):.*?(?=def evaluate_shadow)', new_gen, content, flags=re.DOTALL)

with open('src/dealhunter/identity/evaluator.py', 'w') as f:
    f.write(content)
