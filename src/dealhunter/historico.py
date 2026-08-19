import sqlite3
import statistics
from datetime import datetime, timedelta

def analyze_history(db_path, config, store=None, product=None, explain=False):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    query = '''
        SELECT o.store_id, o.product_id, p.name, s.name, o.price, o.timestamp, o.discount_effective,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit, p.fingerprint
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
        store_id, product_id, p_name, s_name, price, ts_str, d_eff, brand, norm_name, qty, unit, n_qty, n_unit, fp = r
        key = (store_id, product_id)
        if key not in grouped:
            grouped[key] = {
                "product_name": p_name, "store_name": s_name, 
                "brand": brand, "normalized_name": norm_name, "quantity": qty, "unit": unit,
                "normalized_quantity": n_qty, "normalized_unit": n_unit, "fingerprint": fp,
                "obs": []
            }
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", ""))
        except:
            ts = datetime.now()
        grouped[key]["obs"].append({"price": price, "timestamp": ts, "discount_effective": d_eff})
        
    now = datetime.now()
    results = []
    
    min_obs = config.get("min_observations", 1)
    history_days = config.get("history_days", 1.0)
    req_status = config.get("status", [])
    price_drop = config.get("price_drop")
    new_deals = config.get("new_deals", False)
    price_changes = config.get("price_changes", False)
    
    for key, data in grouped.items():
        obs_list = data["obs"]
        if len(obs_list) < min_obs:
            continue
            
        current_price = obs_list[-1]["price"]
        current_discount_effective = obs_list[-1]["discount_effective"]
        
        if len(obs_list) > 1:
            previous_price = obs_list[-2]["price"]
            prev_d_eff = obs_list[-2]["discount_effective"]
        else:
            previous_price = current_price
            prev_d_eff = current_discount_effective
            
        prices_all = [o["price"] for o in obs_list]
        historical_min = min(prices_all)
        historical_max = max(prices_all)
        
        ts_min = obs_list[0]["timestamp"]
        ts_max = obs_list[-1]["timestamp"]
        
        obs_30d = [o["price"] for o in obs_list if o["timestamp"] >= now - timedelta(days=30)]
        obs_7d = [o["price"] for o in obs_list if o["timestamp"] >= now - timedelta(days=7)]
        
        median_30d = statistics.median(obs_30d) if obs_30d else current_price
        median_7d = statistics.median(obs_7d) if obs_7d else current_price
            
        delta_days = (ts_max - ts_min).total_seconds() / 86400.0
        
        hist_ref = median_30d if delta_days >= 30 else median_7d
        historical_discount = (1 - (current_price / hist_ref)) * 100.0 if hist_ref > 0 else 0.0
            
        if delta_days < history_days:
            estado = "INSUFFICIENT_HISTORY"
        elif current_price <= historical_min and current_price < historical_max:
            estado = "NEW_LOW"
        elif historical_discount >= 50.0:
            estado = "REAL_DEAL"
        elif historical_discount >= 30.0:
            estado = "GOOD_DEAL"
        elif current_discount_effective >= 50.0 and historical_discount < 30.0:
            estado = "RAPPI_PROMO"
        else:
            estado = "NORMAL"
            
        # Filters
        if req_status and estado not in req_status:
            continue
            
        if config.get("new_low") and estado != "NEW_LOW":
            continue
            
        if config.get("historical_discount") is not None and historical_discount < config.get("historical_discount"):
            continue
            
        drop_pct = (1 - (current_price / previous_price)) * 100 if previous_price > 0 else 0
        if price_drop is not None and drop_pct < price_drop:
            continue
            
        if new_deals and not (current_discount_effective >= 40 and prev_d_eff < 40): # simplifying logic for new deal
            continue
            
        if price_changes and current_price == previous_price:
            continue
            
        score = 0
        if estado != "INSUFFICIENT_HISTORY":
            if historical_discount > 0: score += min(historical_discount * 1.5, 60)
            if estado == "NEW_LOW": score += 20
            if current_discount_effective >= 50.0: score += 10
            score += min(len(obs_list) * 0.5, 10)
        score = min(max(int(score), 0), 100)
        
        from .normalization import calculate_unit_price
        unit_price = calculate_unit_price(current_price, data["normalized_quantity"])
        
        res = {
            "store_id": key[0],
            "product_id": key[1],
            "product_name": data["product_name"],
            "store_name": data["store_name"],
            "BRAND": data["brand"] or "",
            "QUANTITY": data["quantity"] or "",
            "UNIT": data["unit"] or "",
            "UNIT_PRICE": unit_price if unit_price is not None else "",
            "current_price": current_price,
            "previous_price": previous_price,
            "median_30d": median_30d,
            "historical_min": historical_min,
            "observations_count": len(obs_list),
            "current_discount_effective": current_discount_effective,
            "historical_discount": historical_discount,
            "state": estado,
            "deal_score": score
        }
        
        if explain:
            res["explanation"] = f"Estado: {estado}\nPrecio actual: ${current_price}\nMediana: ${hist_ref}\nCaida: {historical_discount:.1f}%"
            
        results.append(res)
        
    sort_key = config.get("sort", "deal-score")
    
    if sort_key == "unit-price":
        # Missing unit prices go to the bottom
        return sorted(results, key=lambda x: x["UNIT_PRICE"] if x["UNIT_PRICE"] != "" else float('inf'))
    elif sort_key == "price":
        return sorted(results, key=lambda x: x["current_price"])
    elif sort_key == "discount":
        return sorted(results, key=lambda x: x["current_discount_effective"], reverse=True)
    elif sort_key == "historical-discount":
        return sorted(results, key=lambda x: x["historical_discount"], reverse=True)
    else:
        return sorted(results, key=lambda x: x["deal_score"], reverse=True)

def compare_stores(db_path, query, exact_only=False):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT p.product_id, p.store_id, p.name, s.name, o.price,
               p.brand, p.normalized_name, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit, p.fingerprint,
               o.discount_effective
        FROM observations o
        JOIN products p ON o.product_id = p.product_id AND o.store_id = p.store_id
        JOIN stores s ON o.store_id = s.store_id
        WHERE p.name LIKE ? OR p.brand LIKE ? OR o.query_term LIKE ?
        ORDER BY o.timestamp DESC
    ''', (f"%{query}%", f"%{query}%", f"%{query}%"))
    
    rows = c.fetchall()
    
    latest = {}
    for r in rows:
        key = (r[0], r[1])
        if key not in latest:
            latest[key] = {
                "product_id": r[0], "store_id": r[1], "product_name": r[2], "store_name": r[3], "price": r[4],
                "brand": r[5], "normalized_name": r[6], "quantity": r[7], "unit": r[8],
                "normalized_quantity": r[9], "normalized_unit": r[10], "fingerprint": r[11],
                "discount_effective": r[12]
            }
            
    products = list(latest.values())
    if not products:
        return []
        
    from .normalization import compute_match, calculate_unit_price
    
    groups = []
    
    for p in products:
        placed = False
        for g in groups:
            anchor = g[0]
            m_type, m_conf = compute_match(anchor, p)
            if m_type == "EXACT_MATCH" or (not exact_only and m_type == "HIGH_CONFIDENCE_MATCH"):
                p["match_type"] = m_type
                p["match_confidence"] = m_conf
                g.append(p)
                placed = True
                break
        if not placed:
            p["match_type"] = "EXACT_MATCH"
            p["match_confidence"] = 1.00
            groups.append([p])
            
    res = []
    for g in groups:
        g_sorted = sorted(g, key=lambda x: x["price"])
        best_p = g_sorted[0]
        best_price = best_p["price"]
        
        for item in g_sorted:
            diff = ((item["price"] / best_price) - 1) * 100 if best_price > 0 else 0
            u_price = calculate_unit_price(item["price"], item["normalized_quantity"])
            up_str = f"${u_price}/{item['normalized_unit']}" if u_price else ""
            res.append({
                "GRUPO": best_p["product_name"][:20],
                "TIENDA": item["store_name"][:15],
                "PRECIO": f"${item['price']:.2f}",
                "DIFF": f"+{diff:.1f}%" if diff > 0 else "BEST",
                "UNIT_PRICE": up_str,
                "MATCH": item["match_type"].replace("_MATCH", ""),
                "PRODUCTO": item["product_name"][:30]
            })
            
    return res
