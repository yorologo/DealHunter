import urllib.request
import urllib.error
import json
import time
import sys

def fetch_unified_search(query, lat, lng):
    url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
    payload = json.dumps({"query": query, "lat": lat, "lng": lng, "limit": 1000}).encode('utf-8')
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code in [429, 1015]:
            return "RATE_LIMIT"
    except Exception:
        pass
    return None

def run_sweep(strategy="frequency"):
    lat, lng = 19.4326, -99.1332
    HOLDOUT_WORDS = ["bebida", "bebidas", "mascota", "mascotas", "bebe", "bebé", "congelados", "congelado", "farmacia", "higiene", "dulces", "dulce", "hogar"]
    base_queries = ["super", "mercado", "oferta", "descuento", "2x1"]
    
    seen_products = set()
    stores_info = {}
    categories_seen = set()
    brands_seen = set()
    
    query_stats = []
    visited = set()
    candidate_keywords = {}
    
    queries = list(base_queries)
    
    while queries:
        q = queries.pop(0).lower().strip()
        if q in visited or q in HOLDOUT_WORDS:
            continue
            
        visited.add(q)
        print(f"  [Sweep] Querying: '{q}'", file=sys.stderr)
        data = fetch_unified_search(q, lat, lng)
        if data == "RATE_LIMIT":
            print("HTTP 429 DETECTED - STOPPING.", file=sys.stderr)
            break
        elif not data:
            print(f"  [Sweep] No data for '{q}'", file=sys.stderr)
            continue
            
        stores = data.get("stores", []) or []
        new_in_query = 0
        total_in_query = 0
        
        for s in stores:
            s_id = str(s.get("store_id"))
            if s_id not in stores_info:
                stores_info[s_id] = {"name": s.get("store_name", s_id), "products": set(), "queries": set()}
            stores_info[s_id]["queries"].add(q)
            
            for p in s.get("products", []):
                total_in_query += 1
                p_id = str(p.get("product_id"))
                uid = f"{s_id}_{p_id}"
                
                cat = p.get("category_name", "")
                if cat:
                    categories_seen.add(cat)
                    if strategy == "categories" and cat.lower() not in visited and cat.lower() not in HOLDOUT_WORDS:
                        candidate_keywords[cat.lower()] = candidate_keywords.get(cat.lower(), 0) + 1
                        
                brand = p.get("trademark", "")
                if brand:
                    brands_seen.add(brand)
                
                if strategy == "frequency":
                    if cat:
                        for w in cat.split():
                            if len(w) > 3 and w.lower() not in HOLDOUT_WORDS:
                                candidate_keywords[w.lower()] = candidate_keywords.get(w.lower(), 0) + 1
                    pname = p.get("name", "")
                    if pname:
                        for w in pname.split()[:2]:
                            if len(w) > 3 and w.lower() not in HOLDOUT_WORDS:
                                candidate_keywords[w.lower()] = candidate_keywords.get(w.lower(), 0) + 1
                
                if uid not in seen_products:
                    seen_products.add(uid)
                    new_in_query += 1
                    stores_info[s_id]["products"].add(uid)
                    stores_info[s_id]["last_contribution"] = q
        
        eff = new_in_query / len(seen_products) if len(seen_products) > 0 else 0
        query_stats.append({"num": len(query_stats)+1, "query": q, "results": total_in_query, "new": new_in_query, "accumulated": len(seen_products), "novelty_rate": eff})
        
        cands = sorted(candidate_keywords.items(), key=lambda x: x[1], reverse=True)
        added = 0
        for cand, _ in cands:
            c = cand.lower().strip()
            if c not in visited and c not in queries and c not in HOLDOUT_WORDS:
                queries.append(c)
                added += 1
                if added >= 1: break
                
        if len(query_stats) >= 4:
            if all(qs["novelty_rate"] < 0.02 or qs["new"] < 10 for qs in query_stats[-4:]):
                print(f"  [Sweep] Saturación detectada tras {len(query_stats)} queries.", file=sys.stderr)
                break
                
        time.sleep(3)
        
    products_before_holdout = len(seen_products)
    
    holdout_queries = ["bebidas", "mascotas", "farmacia", "higiene", "hogar"]
    holdout_valid_results = 0
    holdout_new_products = 0
    
    for hq in holdout_queries:
        print(f"  [Holdout] Querying: '{hq}'", file=sys.stderr)
        data = fetch_unified_search(hq, lat, lng)
        if data == "RATE_LIMIT":
            print("HTTP 429 DETECTED IN HOLDOUT - STOPPING.", file=sys.stderr)
            break
        if not data:
            continue
            
        stores = data.get("stores", []) or []
        for s in stores:
            s_id = str(s.get("store_id"))
            if s_id not in stores_info:
                stores_info[s_id] = {"name": s.get("store_name", s_id), "products": set(), "queries": set()}
            stores_info[s_id]["queries"].add(hq)
            
            for p in s.get("products", []):
                holdout_valid_results += 1
                uid = f"{s_id}_{p_id}"
                if uid not in seen_products:
                    seen_products.add(uid)
                    holdout_new_products += 1
                    stores_info[s_id]["products"].add(uid)
                    stores_info[s_id]["last_contribution"] = hq
        
        query_stats.append({"num": len(query_stats)+1, "query": f"[HOLDOUT] {hq}", "results": sum(len(s.get("products", [])) for s in stores), "new": -1, "accumulated": len(seen_products), "novelty_rate": -1})
        time.sleep(3)
        
    novelty_rate = holdout_new_products / holdout_valid_results if holdout_valid_results > 0 else 0
    
    state = "SATURATED"
    if novelty_rate > 0.10:
        state = "FALSE_SATURATION"
    elif novelty_rate > 0.03:
        state = "PARTIALLY_SATURATED"
        
    return {
        "products_before_holdout": products_before_holdout,
        "holdout_new": holdout_new_products,
        "novelty_rate": novelty_rate,
        "state": state,
        "stores_info": stores_info,
        "categories": categories_seen,
        "query_stats": query_stats
    }

def print_results(res):
    print(f"Productos antes del holdout: {res['products_before_holdout']}")
    print(f"Productos nuevos del holdout: {res['holdout_new']}")
    print(f"Novelty rate: {res['novelty_rate']*100:.2f}%")
    
    underrepresented_stores = []
    for sid, info in res['stores_info'].items():
        if len(info['products']) < 10 and len(info['products']) > 0:
            underrepresented_stores.append(f"{info['name']} ({len(info['products'])} prod)")
            
    print(f"Tiendas subrepresentadas: {', '.join(underrepresented_stores) if underrepresented_stores else 'Ninguna evidente'}")
    
    all_cats = list(res['categories'])
    expected_cats = ["Mascota", "Bebé", "Higiene", "Farmacia", "Hogar"]
    missing = [c for c in expected_cats if not any(c.lower() in ac.lower() for ac in all_cats)]
    print(f"Categorías subrepresentadas: {', '.join(missing) if missing else 'Ninguna evidente'}")
    
    print(f"Estado final: {res['state']}")

def main():
    print("[*] Ejecutando barrido inicial con estrategia estándar...", file=sys.stderr)
    res = run_sweep(strategy="frequency")
    
    if res["state"] == "FALSE_SATURATION":
        print("\n[*] Falsa saturación detectada. Ajustando algoritmo a estrategia orientada a 'categorías completas'...", file=sys.stderr)
        res = run_sweep(strategy="categories")
        
    print_results(res)
    
    audit_data = {
        "curva_descubrimiento": res["query_stats"],
        "cobertura_tiendas": {sid: {"name": info["name"], "count": len(info["products"])} for sid, info in res["stores_info"].items()}
    }
    with open('/data/data/com.termux/files/home/rappi-deal-hunter/coverage-audit.json', 'w') as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()
