import time
import sys
from datetime import datetime
from .api import fetch_unified_search
from .discounts import calculate_discount
from .core import process_and_insert_product
from .errors import DealHunterError, classify_error
from .checkpoint import RunCheckpoint, save_checkpoint

VERTICALS = {
    "supermercado": ["super", "mercado", "oferta", "descuento", "2x1", "soriana", "fresko", "calii", "costco", "chedraui", "city market", "abastos", "mercado y abarrotes", "bebidas", "abarrotes"],
    "farmacia": ["farmacia", "medicamentos", "vitaminas", "suplementos", "pastillas", "jarabe", "similares", "condesa", "guadalajara", "farmatodo", "benavides", "cuidado digestivo", "salud sexual", "dolor e inflamacion", "gripa y alergias", "salud nutricional", "dermocosmetica", "salud visual", "cuidado de la piel", "cuidado oral", "botiquin"],
    "mascotas": ["mascotas", "perro", "gato", "croquetas", "petco", "maskota"],
    "bebe": ["bebe", "pañales", "formula", "biberon", "toallitas", "papilla", "cuidado del bebe", "infantil"],
    "higiene": ["higiene", "jabon", "shampoo", "desodorante", "pasta dental", "crema", "bed bath", "lush", "l'occitane", "sally beauty", "cuidado personal", "cuidado del cabello", "aseo personal"],
    "hogar": ["hogar", "limpieza", "detergente", "limpiador", "escoba", "suavizante"],
    "tecnologia": ["tecnologia", "cables", "audifonos", "usb", "electronica", "macstore", "lumen", "radioshack"],
    "express": ["miniso", "office depot", "officemax", "papeleria", "libreria", "gandhi", "sanborns", "fantasias miguel", "lego", "juguetron", "juguetes", "regalos"],
    "especialidad": ["dulceria", "dulces", "chocolate", "panaderia", "pasteleria", "pescaderia", "carniceria", "gnc", "toyo foods", "naturista", "organica", "nespresso", "crepa", "snacks", "erectus", "be loving", "de la rosa", "sirilo"],
    "turbo": ["turbo", "turbo fresh", "express", "despensa turbo"],
    "restaurants": ["hamburguesa", "pizza", "sushi", "tacos", "ensalada", "pollo"],
    "conveniencia": ["oxxo", "7 eleven", "conveniencia"],
    "licores": ["licores", "vinos", "cerveza", "tequila", "la playa"],
    "test_run": ["frutarindo"]
}

def is_turbo_store(store_data):
    parent = store_data.get("parent_store_type", "").lower()
    stype = store_data.get("store_type", "").lower()
    turbo_types = ("chiper_home", "chiper_extended", "chiper_express")
    return parent in turbo_types or stype in turbo_types

def is_restaurant(store_data):
    parent = store_data.get("parent_store_type", "").lower()
    return parent == "restaurants"

def matches_filters(p_name, brand, s_name, category, config, d_eff, p_type, eff_price):
    if config.get("min_discount", 0) > d_eff:
        return False
    if config.get("max_discount", 100) < d_eff:
        return False
        
    min_price = config.get("min_price")
    if min_price is not None and eff_price < min_price:
        return False
        
    max_price = config.get("max_price")
    if max_price is not None and eff_price > max_price:
        return False
        
    if config.get("only_nxm") and p_type != "NxM":
        return False
        
    min_promo = config.get("min_promo_discount")
    if min_promo is not None:
        if p_type != "NxM" or d_eff < min_promo:
            return False
            
    promos = config.get("promo", [])
    if promos:
        if p_type == "NxM" and "nxm" not in [x.lower() for x in promos] and "bundle" not in [x.lower() for x in promos]:
            return False
        if p_type == "Direct" and "price" not in [x.lower() for x in promos] and "direct" not in [x.lower() for x in promos]:
            return False
            
    excludes = config.get("exclude", [])
    for ex in excludes:
        if ex.lower() in p_name.lower() or ex.lower() in brand.lower():
            return False
            
    exclude_stores = config.get("exclude_store", [])
    for ex in exclude_stores:
        if ex.lower() in s_name.lower():
            return False
            
    stores = config.get("store", [])
    if stores:
        if not any(st.lower() in s_name.lower() for st in stores):
            return False

    return True

def run_discover(config, lat, lng, conn, run_id, dry_run=False):
    c = conn.cursor()
    verticals_to_run = config.get("vertical", [])
    if not verticals_to_run:
        verticals_to_run = list(VERTICALS.keys())[:-1]
        
    queries_to_run = config.get("query", [])
    
    seen_in_run = set()
    requests_count = 0
    restaurant_category_cache = {}
    max_reqs = config.get("max_requests", 1000)
    start_time = time.time()
    max_time = config.get("max_runtime", 3600)
    
    results = []
    global_state = "COMPLETED"
    error_code = None
    
    # Initialize checkpoint
    checkpoint = RunCheckpoint(
        run_id=run_id,
        mode="discover",
        status="RUNNING",
    )
    
    for v_name in verticals_to_run:
        base_queries = queries_to_run if queries_to_run else VERTICALS.get(v_name, [v_name])
        queries = list(base_queries)
        visited = set()
        candidate_keywords = {}
        
        vertical_total_valid = 0
        state = "LOW_COVERAGE"
        
        checkpoint.current_vertical = v_name
        
        while queries:
            if requests_count >= max_reqs:
                global_state = "REQUEST_BUDGET_REACHED"
                error_code = "REQUEST_BUDGET_REACHED"
                break
            if time.time() - start_time >= max_time:
                global_state = "TIMEOUT"
                error_code = "TIMEOUT"
                break
                
            q = queries.pop(0).lower().strip()
            if q in visited or len(q) < 3:
                continue
                
            visited.add(q)
            if dry_run:
                print(f"[DRY-RUN] Would search: {q}")
                checkpoint.queries_completed += 1
                checkpoint.last_completed_query = q
                continue
                
            print(f"    [{v_name}] Query: '{q}'", file=sys.stderr)
            
            try:
                data = fetch_unified_search(q, lat, lng)
            except Exception as exc:
                err = classify_error(exc)
                print(f"    [{v_name}] Error: {err}", file=sys.stderr)
                if not err.recoverable or err.code in ("HTTP_429", "CLOUDFLARE_LIMIT"):
                    # For rate limits: stop conservatively, preserve what we have
                    global_state = "PARTIAL"
                    error_code = err.code
                    # Save checkpoint before stopping
                    checkpoint.status = "PARTIAL"
                    checkpoint.error_code = err.code
                    checkpoint.requests_made = requests_count

                    save_checkpoint(conn, checkpoint)
                    return global_state, requests_count
                # For recoverable errors, skip this query and continue
                continue
            
            requests_count += 1
            
            if data == "RATE_LIMIT":
                global_state = "PARTIAL"
                error_code = "HTTP_429"
                checkpoint.status = "PARTIAL"
                checkpoint.error_code = "HTTP_429"
                checkpoint.requests_made = requests_count
                save_checkpoint(conn, checkpoint)
                return global_state, requests_count
            elif not data:
                checkpoint.queries_completed += 1
                checkpoint.last_completed_query = q
                continue
                
            stores = data.get("stores", []) or []
            new_in_query = 0
            total_in_query = 0
            
            for s in stores:
                if v_name == "turbo" and not is_turbo_store(s):
                    continue
                if v_name == "restaurants" and not is_restaurant(s):
                    continue
                    
                s_id = str(s.get("store_id"))
                s_name = s.get("store_name", s_id)
                
                c.execute('INSERT OR IGNORE INTO stores (store_id, name, brand, type) VALUES (?, ?, ?, ?)', 
                          (s_id, s_name, s.get("store_brand_name", ""), s.get("parent_store_type", "")))
                
                prods = s.get("products", [])
                
                for p in prods:
                    total_in_query += 1
                    vertical_total_valid += 1
                    p_id = str(p.get("product_id"))
                    uid = f"{s_id}_{p_id}"
                    

                    process_and_insert_product(p, run_id, s_id, s_name, config, q, conn, seen_in_run)
                                      
            # Commit after each query to preserve partial data
            conn.commit()
            
            checkpoint.queries_completed += 1
            checkpoint.last_completed_query = q
            checkpoint.requests_made = requests_count
            
            # Simple keyword expansion based on query results (simplified for length)
            if len(visited) < 10 and not queries_to_run: # only expand if no explicit queries
                for s in stores:
                    if len(queries) < 20:
                        queries.append(s.get("store_name", "").lower())
            
            if not dry_run:
                time.sleep(3)
                
        if global_state not in ("COMPLETED",):
            break
    
    # Final checkpoint update
    checkpoint.status = global_state
    checkpoint.error_code = error_code
    checkpoint.requests_made = requests_count
    save_checkpoint(conn, checkpoint)
    
    c.execute("UPDATE runs SET crawler_mode = ?, coverage_complete = ? WHERE run_id = ?", ("SEARCH_DISCOVERY", 0, run_id))
    conn.commit()
            
    return global_state, requests_count

def run_update(config, lat, lng, conn, run_id, dry_run=False):
    # UPDATE mode aims to refresh known items
    c = conn.cursor()
    
    # We fetch products grouped by store, or just use the names of stores as queries
    # since we can't fetch product IDs directly without the store endpoint.
    # We will use store names and most frequent product queries from observations.
    c.execute("SELECT DISTINCT query_term FROM observations ORDER BY id DESC LIMIT 50")
    queries = [r[0] for r in c.fetchall() if r[0]]
    
    if not queries:
        queries = ["supermercado", "farmacia"]
        
    config["query"] = queries
    return run_discover(config, lat, lng, conn, run_id, dry_run)
