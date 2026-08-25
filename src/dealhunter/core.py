from dealhunter.semantic import classify_membership
from datetime import datetime
from .discounts import calculate_discount
from .normalization import parse_product_name, generate_fingerprint

def matches_filters(name, brand, store, cat, config, eff_discount, promo_type, eff_price):
    if config.get("query"):
        queries = [q.lower() for q in config["query"]]
        found = False
        for q in queries:
            if q in name.lower() or q in brand.lower() or q in store.lower() or q in cat.lower():
                found = True
                break
        if not found:
            return False
            
    if config.get("exclude"):
        for ex in config["exclude"]:
            if ex.lower() in name.lower() or ex.lower() in brand.lower():
                return False

    if config.get("store"):
        stores = [s.lower() for s in config["store"]]
        if store.lower() not in stores:
            return False
            
    if config.get("exclude_store"):
        for ex in config["exclude_store"]:
            if ex.lower() in store.lower():
                return False

    return True

def process_and_insert_product(p, run_id, s_id, s_name, config, q, conn, seen_in_run, provider="rappi"):
    c = conn.cursor()
    pname = p.get("name", "")
    p_id = str(p.get("id") or p.get("product_id", ""))
    uid = f"{s_id}_{p_id}"
    if not p_id or not pname:
        return False
        
    if uid in seen_in_run:
        return False
    seen_in_run.add(uid)

    cat = p.get("category", "")
    cat_source = "provider"
    name_lower = pname.lower()
    
    # Existing fallback logic
    if not cat:
        if "super" in s_name.lower() or "market" in s_name.lower():
            cat = "Supermercado"
            cat_source = "inferred"
        elif "farmacia" in s_name.lower():
            cat = "Farmacia"
            cat_source = "inferred"
        else:
            if "hamburguesa" in name_lower or "burger" in name_lower:
                cat = "Hamburguesas"
                cat_source = "inferred"
            elif "pizza" in name_lower:
                cat = "Pizza"
                cat_source = "inferred"
            elif "sushi" in name_lower or "roll" in name_lower:
                cat = "Sushi"
                cat_source = "inferred"
            elif "taco" in name_lower:
                cat = "Tacos"
                cat_source = "inferred"
            elif "pollo" in name_lower or "wings" in name_lower or "alitas" in name_lower:
                cat = "Pollo"
                cat_source = "inferred"
            elif "helado" in name_lower or "postre" in name_lower or "frappuccino" in name_lower or "pastel" in name_lower or "pay" in name_lower:
                cat = "Postres"
                cat_source = "inferred"
            elif "bebida" in name_lower or "refresco" in name_lower or "coca" in name_lower or "pepsi" in name_lower or "agua" in name_lower or "jugo" in name_lower:
                cat = "Bebidas"
                cat_source = "inferred"
            elif "ensalada" in name_lower or "bowl" in name_lower:
                cat = "Saludable"
                cat_source = "inferred"
            elif "sándwich" in name_lower or "sandwich" in name_lower or "baguette" in name_lower or "sub" in name_lower:
                cat = "Sándwiches"
                cat_source = "inferred"
            elif "café" in name_lower or "cafe" in name_lower or "latte" in name_lower or "espresso" in name_lower:
                cat = "Café"
                cat_source = "inferred"
            elif "papas" in name_lower or "fries" in name_lower:
                cat = "Snacks"
                cat_source = "inferred"

    raw_toppings = p.get("has_toppings")
    has_toppings = 1 if raw_toppings else 0 if raw_toppings is not None else None
    brand = p.get("trademark", "")

    is_in_stock = p.get("in_stock", False) or p.get("is_available", False)
    stock_val = p.get("stock")
    if stock_val is not None and stock_val <= 0:
        is_in_stock = False
        
    availability = "AVAILABLE" if is_in_stock else "UNAVAILABLE"
        
    d_price, d_promo, d_eff, d_src, p_type, p_label, eff_price, eff_real, comm_extra = calculate_discount(p)
    
    if not matches_filters(pname, brand, s_name, cat, config, d_eff, p_type, eff_price):
        return False
        
    img = p.get("image", "")
    if img and not img.startswith("http") and not img.startswith("data:"):
        img = "https://images.rappi.com.mx/products/" + img
        
    norm = parse_product_name(pname, brand)
    fingerprint = generate_fingerprint(
        norm["brand"], norm["normalized_name"],
        norm["normalized_quantity"], norm["normalized_unit"],
        norm["pack_count"]
    )
        
    c.execute('''INSERT INTO products (provider, product_id, store_id, name, brand, image, 
                 normalized_name, quantity, unit, normalized_quantity, normalized_unit,
                 fingerprint, pack_count, category, has_toppings, category_source)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT(provider, store_id, product_id) DO UPDATE SET
                 brand = COALESCE(NULLIF(brand, ''), excluded.brand),
                 normalized_name = COALESCE(NULLIF(normalized_name, ''), excluded.normalized_name),
                 quantity = COALESCE(quantity, excluded.quantity),
                 unit = COALESCE(NULLIF(unit, ''), excluded.unit),
                 normalized_quantity = COALESCE(normalized_quantity, excluded.normalized_quantity),
                 normalized_unit = COALESCE(NULLIF(normalized_unit, ''), excluded.normalized_unit),
                 pack_count = COALESCE(pack_count, excluded.pack_count),
                 category = COALESCE(NULLIF(excluded.category, ''), category),
                 has_toppings = COALESCE(excluded.has_toppings, has_toppings),
                 category_source = COALESCE(NULLIF(excluded.category_source, 'unknown'), category_source),
                 image = COALESCE(NULLIF(image, ''), excluded.image),
                 name = COALESCE(NULLIF(name, ''), excluded.name),
                 fingerprint = CASE 
                    WHEN NULLIF(brand, '') IS NULL AND NULLIF(excluded.brand, '') IS NOT NULL THEN excluded.fingerprint
                    WHEN quantity IS NULL AND excluded.quantity IS NOT NULL THEN excluded.fingerprint
                    WHEN NULLIF(fingerprint, '') IS NULL THEN excluded.fingerprint
                    ELSE fingerprint
                 END
                 ''',
              (provider, p_id, s_id, pname, brand, img,
               norm["normalized_name"], norm["quantity"], norm["unit"], 
               norm["normalized_quantity"], norm["normalized_unit"], fingerprint,
               norm["pack_count"], cat, has_toppings, cat_source))
    
    # Phase 3A: Persist RAW memberships
    import json
    from datetime import datetime as _dt
    memberships = p.get("memberships", [])
    now = _dt.now().isoformat()
    for m in memberships:
        raw_type = m.get("raw_type", "")
        raw_name = m.get("raw_name", "")
        raw_id = str(m.get("raw_id", ""))
        path_str = json.dumps(m.get("path", []))
        # Re-classify membership on every observation
        stype, sreason = classify_membership(raw_name, cat, cat_source, raw_type)
        
        c.execute('''INSERT INTO product_memberships
                     (provider, store_id, product_id, raw_type, raw_name, raw_id, path, source, last_seen, semantic_type, semantic_reason)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                     ON CONFLICT(provider, store_id, product_id, raw_type, raw_name, path) DO UPDATE SET
                     last_seen=excluded.last_seen, raw_id=excluded.raw_id,
                     semantic_type=excluded.semantic_type, semantic_reason=excluded.semantic_reason
                  ''', (provider, s_id, p_id, raw_type, raw_name, raw_id, path_str, "catalog_sync", now, stype, sreason))
    
    # Phase 3A.1: Safe Facet Reconciliation
    # Remove stale memberships for this product that were not seen in this complete observation
    c.execute('''DELETE FROM product_memberships 
                 WHERE provider=? AND store_id=? AND product_id=? AND last_seen != ?''', 
              (provider, s_id, p_id, now))
    
    from dealhunter.db import CURRENT_SCHEMA_VERSION
    if CURRENT_SCHEMA_VERSION >= 12:
        c.execute('''INSERT OR IGNORE INTO observations (provider, run_id, store_id, product_id, price, original_price, stock, timestamp, 
                     discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term, availability,
                     has_pro_offer, pro_price, pro_discount_effective, limit_info)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (provider, run_id, s_id, p_id, eff_price, eff_real, stock_val, datetime.now().isoformat(), 
                      d_price, d_promo, d_eff, d_src, p_type, p_label, q, availability,
                      1 if comm_extra.get("has_pro_offer") else (None if availability == "UNAVAILABLE" else 0),
                      comm_extra.get("pro_price"),
                      comm_extra.get("pro_discount_effective"),
                      str(comm_extra.get("limit")) if comm_extra.get("limit") is not None else None))
    else:
        c.execute('''INSERT OR IGNORE INTO observations (provider, run_id, store_id, product_id, price, original_price, stock, timestamp, 
                     discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term, availability)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (provider, run_id, s_id, p_id, eff_price, eff_real, stock_val, datetime.now().isoformat(), 
                      d_price, d_promo, d_eff, d_src, p_type, p_label, q, availability))
    return True
