import statistics
from datetime import datetime, timedelta

from .db import setup_db
from .price_intelligence import compute_price_metrics
from .normalization import calculate_unit_price, compute_match, format_unit_price

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
            
        unit_price = format_unit_price(metrics["current_price"], data["normalized_quantity"], data.get("normalized_unit"))
        
        res = {
            "store_id": key[0],
            "product_id": key[1],
            "product_name": data["product_name"],
            "store_name": data["store_name"],
            "BRAND": data["brand"] or "",
            "QUANTITY": data["quantity"] or "",
            "UNIT": data["unit"] or "",
            "UNIT_PRICE": unit_price,
            "current_price": metrics["current_price"],
            "historical_min": metrics["historical_min"],
            "median_30d": metrics["median_30d"],
            "historical_average": metrics["historical_average"],
            "previous_price": metrics["previous_price"],
            "price_change": metrics["price_change"],
            "price_change_percent": metrics["price_change_percent"],
            "discount_vs_median_30d": metrics["discount_vs_median_30d"],
            "distance_from_historical_min": metrics["distance_from_historical_min"],
            "deal_status": estado,
            "reason": metrics["reason"],
            "is_suspicious_reference": metrics.get("is_suspicious_reference", False)
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


def compare_with_anchor(db_path, store_id, product_id):
    from dealhunter.normalization import compute_match
    conn = setup_db(db_path)
    c = conn.cursor()
    
    # 1. Fetch anchor product
    c.execute('''
        SELECT p.product_id, p.store_id, p.name, s.name,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit,
               p.fingerprint, p.pack_count
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        WHERE p.product_id = ? AND p.store_id = ?
    ''', (product_id, store_id))
    
    row = c.fetchone()
    if not row:
        return []
        
    anchor = {
        "product_id": row[0], "store_id": row[1], "product_name": row[2], "store_name": row[3],
        "brand": row[4], "normalized_name": row[5], "quantity": row[6], "unit": row[7],
        "normalized_quantity": row[8], "normalized_unit": row[9], "fingerprint": row[10],
        "pack_count": row[11], "obs": []
    }
    
    # 2. Find candidates (use brand if available, otherwise name parts, limited to avoid full DB scan)
    # A simple approach: use normalized_name if available, else name
    search_term = anchor["normalized_name"] or anchor["product_name"]
    # We can just take the first word or two to cast a wide but limited net
    words = [w for w in search_term.split() if len(w) > 2][:2]
    
    if not words:
        words = [search_term.split()[0]] if search_term.split() else [search_term]
        
    conditions = []
    params = []
    for w in words:
        conditions.append("(p.name LIKE ? OR p.normalized_name LIKE ? OR p.brand LIKE ?)")
        params.extend([f"%{w}%", f"%{w}%", f"%{w}%"])
        
    query = f'''
        SELECT p.product_id, p.store_id, p.name, s.name,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit,
               p.fingerprint, p.pack_count
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        WHERE {' AND '.join(conditions)}
        LIMIT 200
    '''
    c.execute(query, params)
    candidate_rows = c.fetchall()
    
    products_map = {}
    for r in candidate_rows:
        key = (r[0], r[1])
        products_map[key] = {
            "product_id": r[0], "store_id": r[1], "product_name": r[2], "store_name": r[3],
            "brand": r[4], "normalized_name": r[5], "quantity": r[6], "unit": r[7],
            "normalized_quantity": r[8], "normalized_unit": r[9], "fingerprint": r[10],
            "pack_count": r[11], "obs": []
        }
        
    # Ensure anchor is in map even if search missed it
    products_map[(anchor["product_id"], anchor["store_id"])] = anchor
        
    # Fetch observations for these candidates
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
                from datetime import datetime
                ts = datetime.fromisoformat(ts_str.replace("Z", ""))
            except:
                from datetime import datetime
                ts = datetime.now()
            products_map[key]["obs"].append({"price": price, "timestamp": ts, "original_price": orig_price})
            
    # Filter valid matches using compute_match
    valid_matches = []
    
    # We will deduplicate by store_id: we want the best representative from each store
    # if there are multiple matches in the same store. But wait, if multiple items match in the same store, 
    # we pick the one with the lowest price. But if the anchor is from that store, it MUST be the representative.
    
    for key, p in products_map.items():
        if not p["obs"]:
            continue
        if p["product_id"] == anchor["product_id"] and p["store_id"] == anchor["store_id"]:
            m_type = "EXACT_MATCH"
        else:
            m_type, m_conf = compute_match(anchor, p)
            
        if m_type != "NO_MATCH":
            metrics = compute_price_metrics(p["obs"])
            if metrics:
                p["price"] = metrics["current_price"]
                p["metrics"] = metrics
                p["match_type"] = m_type
                valid_matches.append(p)
                
    if not valid_matches:
        return []
        
    # Deduplicate by store_id
    store_best = {}
    for p in valid_matches:
        sid = p["store_id"]
        if sid not in store_best:
            store_best[sid] = p
        else:
            # If we already have the anchor for this store, keep it
            if store_best[sid]["product_id"] == anchor["product_id"]:
                continue
            # If the new one is the anchor, use it
            if p["product_id"] == anchor["product_id"]:
                store_best[sid] = p
            else:
                # Pick the cheaper one
                if p["price"] < store_best[sid]["price"]:
                    store_best[sid] = p
                    
    final_matches = list(store_best.values())
    
    # Sort by price
    final_matches.sort(key=lambda x: x["price"])
    best_current = final_matches[0]
    
    res = []
    for item in final_matches:
        up_str = format_unit_price(item["price"], item["normalized_quantity"], item["normalized_unit"])
        metrics = item["metrics"]
        
        # Calculate VS_MEDIAN correctly using the discount_vs_median_30d
        discount_vs_median = metrics["discount_vs_median_30d"]
        if discount_vs_median > 0:
            vs_median_str = f"↓ {discount_vs_median:.1f}%"
        elif discount_vs_median < 0:
            vs_median_str = f"↑ {-discount_vs_median:.1f}%"
        else:
            vs_median_str = "0%"
            
        res.append({
            "product_id": item["product_id"],
            "store_id": item["store_id"],
            "TIENDA": item["store_name"][:15],
            "PRECIO": f"${item['price']:.2f}",
            "DIFF": f"+{((item['price'] / best_current['price']) - 1) * 100:.1f}%" if item['price'] > best_current['price'] else "BEST",
            "UNIT_PRICE": up_str,
            "MEDIAN_30D": f"${metrics['median_30d']:.2f}",
            "HIST_MIN": f"${metrics['historical_min']:.2f}",
            "VS_MEDIAN": vs_median_str,
            "STATUS": metrics["status"],
            "MATCH": item["match_type"].replace("_MATCH", ""),
            "PRODUCTO": item["product_name"][:30],
            "price_val": item["price"] # raw value for diff
        })
        
    return {
        "anchor_name": anchor["product_name"],
        "matches": res
    }

