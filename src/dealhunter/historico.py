import sqlite3
import statistics
from datetime import datetime, timedelta

def analyze_history(db_path, config, store=None, product=None, explain=False):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    query = '''
        SELECT o.store_id, o.product_id, p.name, s.name, o.price, o.timestamp, o.discount_effective
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
        store_id, product_id, p_name, s_name, price, ts_str, d_eff = r
        key = (store_id, product_id)
        if key not in grouped:
            grouped[key] = {"product_name": p_name, "store_name": s_name, "obs": []}
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
        
        res = {
            "store_id": key[0],
            "product_id": key[1],
            "product_name": data["product_name"],
            "store_name": data["store_name"],
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
        
    return sorted(results, key=lambda x: x["deal_score"], reverse=True)

def compare_stores(db_path, query):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT p.name, s.name, o.price
        FROM observations o
        JOIN products p ON o.product_id = p.product_id AND o.store_id = p.store_id
        JOIN stores s ON o.store_id = s.store_id
        WHERE p.name LIKE ?
        ORDER BY o.timestamp DESC
    ''', (f"%{query}%",))
    
    # We want latest per store-product. 
    # simplified group:
    latest = {}
    for r in c.fetchall():
        key = (r[0], r[1])
        if key not in latest:
            latest[key] = r[2]
            
    res = []
    for (p_name, s_name), price in latest.items():
        res.append({"product": p_name, "store": s_name, "price": price})
    return res
