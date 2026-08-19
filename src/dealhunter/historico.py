import statistics
from datetime import datetime, timedelta

from .db import setup_db
from .price_intelligence import compute_price_metrics
from .normalization import calculate_unit_price, compute_match

def analyze_history(db_path, config, store=None, product=None):
    conn = setup_db(db_path)
    c = conn.cursor()
    
    query = '''
        SELECT o.store_id, o.product_id, p.name, s.name, o.price, o.timestamp, o.discount_effective, o.original_price,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit,
               p.fingerprint, p.pack_count
        FROM observations o
        JOIN products p ON o.product_id = p.product_id AND o.store_id = p.store_id
        JOIN stores s ON o.store_id = s.store_id
    '''
    
    params = []
    conditions = []
    if store:
        conditions.append("o.store_id = ?")
        params.append(store)
    if product:
        conditions.append("o.product_id = ?")
        params.append(product)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY o.timestamp ASC"
    c.execute(query, params)
    rows = c.fetchall()
    
    grouped = {}
    for r in rows:
        store_id, product_id, p_name, s_name, price, ts_str, d_eff, orig_price, brand, norm_name, qty, unit, n_qty, n_unit, fp, pack_count = r
        key = (store_id, product_id)
        if key not in grouped:
            grouped[key] = {
                "product_name": p_name, "store_name": s_name, 
                "brand": brand, "normalized_name": norm_name, "quantity": qty, "unit": unit,
                "normalized_quantity": n_qty, "normalized_unit": n_unit, "fingerprint": fp,
                "pack_count": pack_count,
                "obs": []
            }
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", ""))
        except:
            ts = datetime.now()
        grouped[key]["obs"].append({"price": price, "timestamp": ts, "discount_effective": d_eff, "original_price": orig_price})
        
    results = []
    
    req_status = config.get("status", [])
    if isinstance(req_status, str):
        req_status = [req_status]
        
    for key, data in grouped.items():
        obs_list = data["obs"]
        
        metrics = compute_price_metrics(obs_list)
        if not metrics:
            continue
            
        estado = metrics["status"]
        
        if req_status and estado not in req_status:
            continue
            
        unit_price = calculate_unit_price(metrics["current_price"], data["normalized_quantity"])
        
        res = {
            "store_id": key[0],
            "product_id": key[1],
            "product_name": data["product_name"],
            "store_name": data["store_name"],
            "BRAND": data["brand"] or "",
            "QUANTITY": data["quantity"] or "",
            "UNIT": data["unit"] or "",
            "UNIT_PRICE": unit_price if unit_price is not None else "",
            "current_price": metrics["current_price"],
            "historical_min": metrics["historical_min"],
            "median_30d": metrics["median_30d"],
            "historical_average": metrics["historical_average"],
            "price_change": metrics["price_change"],
            "price_change_percent": metrics["price_change_percent"],
            "discount_vs_median_30d": metrics["discount_vs_median_30d"],
            "distance_from_historical_min": metrics["distance_from_historical_min"],
            "deal_status": estado,
            "reason": metrics["reason"]
        }
        
        results.append(res)
        
    sort_key = config.get("sort", "discount")
    if sort_key == "discount":
        return sorted(results, key=lambda x: x["discount_vs_median_30d"], reverse=True)
    elif sort_key == "price":
        return sorted(results, key=lambda x: x["current_price"])
    else:
        return sorted(results, key=lambda x: x["discount_vs_median_30d"], reverse=True)

def compare_stores(db_path, query, exact_only=False, no_fuzzy=False):
    conn = setup_db(db_path)
    c = conn.cursor()
    # We fetch all observations for products matching the query to compute metrics
    c.execute('''
        SELECT p.product_id, p.store_id, p.name, s.name,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit,
               p.fingerprint, p.pack_count
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        WHERE p.name LIKE ? OR p.brand LIKE ?
    ''', (f"%{query}%", f"%{query}%"))
    
    rows = c.fetchall()
    if not rows:
        return []
        
    products_map = {}
    for r in rows:
        key = (r[0], r[1]) # product_id, store_id
        products_map[key] = {
            "product_id": r[0], "store_id": r[1], "product_name": r[2], "store_name": r[3],
            "brand": r[4], "normalized_name": r[5], "quantity": r[6], "unit": r[7],
            "normalized_quantity": r[8], "normalized_unit": r[9], "fingerprint": r[10],
            "pack_count": r[11], "obs": []
        }
        
    c.execute('''
        SELECT product_id, store_id, price, timestamp, original_price
        FROM observations
        ORDER BY timestamp ASC
    ''')
    obs_rows = c.fetchall()
    
    for r in obs_rows:
        pid, sid, price, ts_str, orig_price = r
        key = (pid, sid)
        if key in products_map:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", ""))
            except:
                ts = datetime.now()
            products_map[key]["obs"].append({"price": price, "timestamp": ts, "original_price": orig_price})
            
    products = []
    for p in products_map.values():
        if not p["obs"]:
            continue
        metrics = compute_price_metrics(p["obs"])
        if metrics:
            p["price"] = metrics["current_price"]
            p["metrics"] = metrics
            products.append(p)
            
    groups = []
    
    for p in products:
        placed = False
        for g in groups:
            anchor = g[0]
            m_type, m_conf = compute_match(anchor, p)
            
            is_match = False
            if m_type == "EXACT_MATCH":
                is_match = True
            elif not exact_only and m_type == "HIGH_CONFIDENCE_MATCH":
                is_match = True
            elif not exact_only and not no_fuzzy and m_type == "FUZZY_MATCH":
                is_match = True
                
            if is_match:
                p["match_type"] = m_type
                g.append(p)
                placed = True
                break
        if not placed:
            p["match_type"] = "EXACT_MATCH"
            groups.append([p])
            
    res = []
    for g in groups:
        g_sorted = sorted(g, key=lambda x: x["price"])
        
        # Calculate bests using historical data (best_current_price, best_unit_price, best_historical_value)
        best_current = min(g_sorted, key=lambda x: x["price"])
        
        for item in g_sorted:
            u_price = calculate_unit_price(item["price"], item["normalized_quantity"])
            up_str = f"${u_price}/{item['normalized_unit']}" if u_price else ""
            metrics = item["metrics"]
            median = metrics["median_30d"]
            hist_min = metrics["historical_min"]
            discount_vs_median = metrics["discount_vs_median_30d"]
            status = metrics["status"]
            
            res.append({
                "GRUPO": best_current["product_name"][:20],
                "TIENDA": item["store_name"][:15],
                "PRECIO": f"${item['price']:.2f}",
                "DIFF": f"+{((item['price'] / best_current['price']) - 1) * 100:.1f}%" if item['price'] > best_current['price'] else "BEST",
                "UNIT_PRICE": up_str,
                "MEDIAN_30D": f"${median:.2f}",
                "HIST_MIN": f"${hist_min:.2f}",
                "VS_MEDIAN": f"-{discount_vs_median:.1f}%" if discount_vs_median > 0 else f"+{-discount_vs_median:.1f}%",
                "STATUS": status,
                "MATCH": item["match_type"].replace("_MATCH", ""),
                "PRODUCTO": item["product_name"][:30]
            })
            
    return res
