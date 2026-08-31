import sqlite3
from dealhunter.db import get_default_db_path, db_status
from dealhunter.historico import analyze_history
from dealhunter.alerts import AlertEngine

def get_home_metrics(db_path):
    stats = db_status(db_path)
    
    # We use analyze_history lightly if possible, but actually we need to show
    # - newest NEW_LOW (top 5)
    # - newest REAL_DEAL (top 5)
    # - biggest price drops (PRICE_DROP)
    
    c = sqlite3.connect(db_path).cursor()
    c.execute("SELECT COUNT(*) FROM alerts WHERE seen = 0")
    new_alerts = c.fetchone()[0]
    
    return {
        "stats": stats,
        "new_alerts": new_alerts
    }

def get_home_deals(db_path, filters=None):
    if filters is None: filters = {}
    # Using analyze_history from historico
    new_lows = analyze_history(db_path, {**filters, "status": ["NEW_LOW"], "sort": "discount"})
    real_deals = analyze_history(db_path, {**filters, "status": ["REAL_DEAL"], "sort": "discount"})
    good_prices = analyze_history(db_path, {**filters, "status": ["GOOD_PRICE"], "sort": "discount"})
    
    # Top 5 for each category to show on home
    return {
        "new_lows": new_lows[:5],
        "real_deals": real_deals[:5],
        "good_prices": good_prices[:5],
    }

def get_watchlist(db_path, filters=None):
    c = sqlite3.connect(db_path).cursor()
    try:
        c.execute("SELECT query, store_filter, target_price FROM watchlist WHERE enabled = 1")
        return [{"query": r[0], "store": r[1], "target_price": r[2]} for r in c.fetchall()]
    except sqlite3.OperationalError:
        return []

from dealhunter.historico import compute_price_metrics, compare_stores, compare_with_anchor
from dealhunter.normalization import format_unit_price
from datetime import datetime

def get_product_detail(db_path, provider, store_id, product_id):
    c = sqlite3.connect(db_path).cursor()
    c.execute('''
        SELECT p.provider, p.product_id, p.store_id, p.name, s.name, s.type as store_type, p.brand, 
               p.category, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit, p.pack_count
        FROM products p
        JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
        WHERE p.provider = ? AND p.store_id = ? AND p.product_id = ?
    ''', (provider, store_id, product_id))
    row = c.fetchone()
    if not row:
        return None
        
    p = {
        "provider": row[0],
        "product_id": row[1],
        "store_id": row[2],
        "product_name": row[3],
        "store_name": row[4],
        "store_type": row[5],
        "brand": row[6],
        "category": row[7],
        "quantity": row[8],
        "unit": row[9],
        "normalized_quantity": row[10],
        "normalized_unit": row[11],
        "pack_count": row[12]
    }
    
    # Get obs
    c.execute('''
        SELECT price, timestamp, original_price, availability, discount_promotion, promotion_type, promotion_label, run_id, has_pro_offer, pro_price, pro_discount_effective
        FROM trusted_observations
        WHERE provider = ? AND store_id = ? AND product_id = ?
        ORDER BY timestamp ASC, id ASC
    ''', (provider, store_id, product_id))
    
    obs_rows = c.fetchall()
    
    obs = []
    for r in obs_rows:

        if r[1]:
            try:
                ts = datetime.fromisoformat(r[1].replace("Z", ""))
            except:
                ts = datetime.now()
        else:
            ts = datetime(1970, 1, 1)

        obs.append({
            "price": r[0],
            "timestamp": ts,
            "original_price": r[2],
            "availability": r[3],
            "discount_promotion": r[4],
            "promotion_type": r[5],
            "promotion_label": r[6],
            "run_id": r[7],
            "has_pro_offer": bool(r[8]),
            "pro_price": r[9],
            "pro_discount_effective": r[10],
        })
        
    p["observations"] = obs
    p["metrics"] = compute_price_metrics(obs) if obs else None
    if p["metrics"]:
        p["unit_price"] = format_unit_price(p["metrics"]["current_price"], p["normalized_quantity"], p["normalized_unit"])
        
        # Calculate Deal Score
        from dealhunter.score import calculate_deal_score
        # we don't have market min price here easily without another query, so we skip it (returns None)
        score_data = calculate_deal_score(p["metrics"], p["metrics"]["current_price"], p["metrics"].get("original_price"), None)
        p["score_data"] = score_data
        p["deal_score"] = score_data["score"]
    else:
        p["unit_price"] = None
        p["deal_score"] = None
        p["score_data"] = None
        
    # Alerts
    c.execute(
        "SELECT alert_type, triggered_at FROM alerts WHERE provider = ? AND product_id = ? AND store_id = ? ORDER BY triggered_at DESC",
        (provider, product_id, store_id),
    )
    alerts = c.fetchall()
    p["alerts"] = [{"alert_type": a[0], "triggered_at": a[1]} for a in alerts]
    
    # Watchlist
    c.execute("SELECT target_price FROM watchlist WHERE query = ? AND enabled = 1", (p["product_name"],))
    w = c.fetchone()
    p["target_price"] = w[0] if w else None
    
    return p

def get_product_compare(db_path, product_name):
    from dealhunter.historico import compare_stores
    res = compare_stores(db_path, product_name)
    return res


def get_anchor_compare(db_path, provider, store_id, product_id):
    return compare_with_anchor(db_path, provider, store_id, product_id)


def enrich_products_with_metrics(db_path, products):
    # products is a list of dicts with product_id, store_id, etc.
    # We fetch observations for ONLY these products
    if not products:
        return products
        
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # We can batch query observations
    conds = []
    params = []
    for p in products:
        conds.append("(provider = ? AND product_id = ? AND store_id = ?)")
        params.extend([p["provider"], p["product_id"], p["store_id"]])
        
    query = f"SELECT provider, store_id, product_id, price, timestamp, original_price FROM trusted_observations WHERE {' OR '.join(conds)} ORDER BY timestamp ASC, id ASC"
    c.execute(query, params)
    obs_rows = c.fetchall()
    
    obs_map = {}
    for r in obs_rows:
        key = (r[0], r[1], r[2])
        if key not in obs_map:
            obs_map[key] = []

        if r[4]:
            try:
                ts = datetime.fromisoformat(r[4].replace("Z", ""))
            except:
                ts = datetime.now()
        else:
            ts = datetime(1970, 1, 1)

        obs_map[key].append({"price": r[3], "timestamp": ts, "original_price": r[5]})
        
    for p in products:
        key = (p["provider"], p["store_id"], p["product_id"])
        obs = obs_map.get(key, [])
        metrics = compute_price_metrics(obs)
        if metrics:
            p["metrics"] = metrics
            p["unit_price"] = format_unit_price(metrics["current_price"], p["normalized_quantity"], p["normalized_unit"])
        else:
            p["metrics"] = None
            p["unit_price"] = None
            
    conn.close()
    return products







def get_deals(db_path, filters, sort, page, per_page=25):
    # This serves the /deals page
    # It combines Price Intelligence (deal_status) and Alerts (alert_type)
    from dealhunter.historico import analyze_history
    from dealhunter.alerts import AlertEngine
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Gather all deals based on filters
    items = []
    
    tab = filters.get("tab", "todo")
    selected_providers = set(filters.get("providers") or [])
    history_scope = {"providers": list(selected_providers)} if selected_providers else {}

    def provider_visible(item):
        return not selected_providers or item.get("provider") in selected_providers
    
    if tab in ["NEW_LOW", "REAL_DEAL", "GOOD_PRICE"]:
        # Price Intelligence deals
        res = analyze_history(db_path, {**history_scope, "status": tab})
        for r in res:
            items.append({
                "type": "pi", # Price Intelligence
                "data": r,
                "sort_date": r.get("timestamp", datetime.now()) # wait, analyze_history doesn't return timestamp of deal. It returns current_price. We can use latest observation.
            })
    elif tab in ["PRICE_DROP", "TARGET_PRICE", "BACK_IN_STOCK"]:
        # Alerts
        engine = AlertEngine(db_path)
        alerts = [
            alert for alert in engine.get_alerts(alert_type=tab, top=1000)
            if provider_visible(alert)
        ]
        for a in alerts:
            # We need to enrich it to look like a deal card
            a["unit_price"] = ""
            items.append({
                "type": "alert",
                "data": a,
                "sort_date": datetime.fromisoformat(a["triggered_at"])
            })
    elif tab == "SUSPICIOUS_REFERENCE_PRICE":
        # We must find products where metrics say suspicious
        res = analyze_history(db_path, history_scope)
        for r in res:
            if r.get("is_suspicious_reference"):
                item_data = {
                    "provider": r["provider"],
                    "product_id": r["product_id"],
                    "store_id": r["store_id"],
                    "product_name": r["product_name"],
                    "store_name": r["store_name"],
                    "brand": r.get("BRAND"),
                    "quantity": r.get("QUANTITY"),
                    "unit": r.get("UNIT"),
                    "current_price": r["current_price"],
                    "unit_price": r.get("UNIT_PRICE"),
                    "metrics": {
                        "deal_status": r["deal_status"],
                        "original_price": r.get("original_price"),
                        "is_suspicious_reference": r.get("is_suspicious_reference"),
                        "discount_vs_median_30d": r.get("discount_vs_median_30d"),
                        "reason": r.get("reason"),
                        "historical_min": r.get("historical_min"),
                        "historical_max": r.get("historical_max"),
                        "median_30d": r.get("median_30d"),
                        "historical_average": r.get("historical_average"),
                        "previous_price": r.get("previous_price"),
                    }
                }
                items.append({
                    "type": "pi",
                    "data": item_data,
                    "sort_date": datetime.now()
                })
    else:
        # Todo
        res = analyze_history(
            db_path,
            {**history_scope, "status": ["NEW_LOW", "REAL_DEAL", "GOOD_PRICE"]},
        )
        for r in res:
            item_data = {
                "provider": r["provider"],
                "product_id": r["product_id"],
                "store_id": r["store_id"],
                "product_name": r["product_name"],
                "store_name": r["store_name"],
                "brand": r.get("BRAND"),
                "quantity": r.get("QUANTITY"),
                "unit": r.get("UNIT"),
                "current_price": r["current_price"],
                "unit_price": r.get("UNIT_PRICE"),
                "metrics": {
                    "deal_status": r["deal_status"],
                    "original_price": r.get("original_price"),
                    "is_suspicious_reference": r.get("is_suspicious_reference"),
                    "discount_vs_median_30d": r.get("discount_vs_median_30d"),
                    "reason": r.get("reason"),
                    "historical_min": r.get("historical_min"),
                    "historical_max": r.get("historical_max"),
                    "median_30d": r.get("median_30d"),
                    "historical_average": r.get("historical_average"),
                    "previous_price": r.get("previous_price"),
                }
            }
            items.append({
                "type": "pi",
                "data": item_data,
                "sort_date": datetime.now()
            })
            
        engine = AlertEngine(db_path)
        alerts = [
            alert for alert in engine.get_alerts(top=1000)
            if provider_visible(alert)
        ]
        for a in alerts:
            if a["alert_type"] not in ["NEW_LOW", "REAL_DEAL"]: # Exclude these so we don't double count if they are already in PI
                a["unit_price"] = ""
                items.append({
                    "type": "alert",
                    "data": a,
                    "sort_date": datetime.fromisoformat(a["triggered_at"])
                })
                
    # Sort
    # Sorting options: mejor oportunidad, mayor caída, menor precio, mejor precio unitario, mayor descuento vs mediana, reciente, A-Z
    def get_sort_key(item):
        d = item["data"]
        if sort == "recent":
            return item["sort_date"].timestamp() * -1
        elif sort == "price":
            return d.get("current_price", 999999)
        elif sort == "discount":
            return d.get("discount_vs_median_30d", 0) * -1
        elif sort == "drop":
            if item["type"] == "alert" and d.get("alert_type") == "PRICE_DROP":
                if d.get("previous_price") and d.get("previous_price") > 0:
                    return ((1 - (d["current_price"] / d["previous_price"])) * 100) * -1
            return 0
        elif sort == "name":
            return d.get("product_name", "")
        else: # opportunity
            status = d.get("deal_status", "")
            if status == "NEW_LOW": return 0
            if status == "REAL_DEAL": return 1
            if status == "GOOD_PRICE": return 2
            return 3
            
    items.sort(key=get_sort_key)
    
    # Paginate
    offset = (page - 1) * per_page
    paginated = items[offset:offset+per_page]
    
    # Enrich alerts with full product detail (for unit price and image)
    for i in paginated:
        if i["type"] == "alert":
            c.execute(
                "SELECT normalized_quantity, normalized_unit FROM products WHERE provider=? AND product_id=? AND store_id=?",
                (i["data"]["provider"], i["data"]["product_id"], i["data"]["store_id"]),
            )
            row = c.fetchone()
            if row:
                i["data"]["UNIT_PRICE"] = format_unit_price(i["data"]["current_price"], row[0], row[1])
                
    return {
        "items": paginated,
        "total": len(items),
        "page": page,
        "pages": (len(items) + per_page - 1) // per_page
    }


def get_catalog(db_path, filters, sort, page, per_page=25):
    import sqlite3
    from dealhunter.query_layer import build_faceted_query
    from dealhunter.config import get_merged_config
    from dealhunter.eligibility import EligibilityEngine
    from dealhunter.config import get_merged_config
    from dealhunter.eligibility import EligibilityEngine
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    facets = _translate_filters(filters, sort, page, per_page)
    config = get_merged_config(None)
    engine = EligibilityEngine(config)
    q, count_q, params = build_faceted_query(facets, config)
    
    c.execute(count_q, params)
    total = c.fetchone()[0]
    
    c.execute(q, params)
    rows = c.fetchall()
    
    products = []
    for r in rows:
        provider = r[23] if len(r) > 23 else 'rappi'
        has_pro = bool(r[13])
        elig = engine.evaluate(provider, has_pro)
        req_mem = engine.map_offer_to_membership(provider, has_pro)
        
        products.append({
            "product_id": r[0],
            "store_id": r[1],
            "product_name": r[2],
            "store_name": r[3],
            "store_type": r[4],
            "brand": r[6],
            "category": r[7],
            "current_price": r[8],
            "original_price": r[9],
            "discount_percent": r[10] or 0.0,
            "savings": (r[9] - r[8]) if r[9] and r[8] else 0.0,
            "promotion_type": r[11],
            "promotion_label": r[12],
            "has_pro_offer": has_pro,
            "pro_price": r[14],
            "pro_discount_effective": r[15],
            "limit_info": r[16],
            "availability": r[17],
            "ts": r[18],
            "quantity": r[19],
            "unit": r[20],
            "normalized_quantity": r[21],
            "normalized_unit": r[22],
            "provider": provider,
            "ranking_eligible": elig["ranking_eligible"],
            "requires_membership": req_mem,
        })
        
    conn.close()
    
    items = enrich_products_with_metrics(db_path, products)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page
    }



def get_categories(db_path, filters=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    providers = (filters or {}).get("providers") or []
    provider_sql = ""
    params = []
    if providers:
        provider_sql = f" AND p.provider IN ({','.join('?' for _ in providers)})"
        params.extend(providers)
    # Use real category from products, fallback to Uncategorized
    c.execute(f'''
        SELECT COALESCE(NULLIF(TRIM(p.category), ''), 'Uncategorized') as cat_name, 
               COUNT(*),
               COUNT(DISTINCT p.provider || char(31) || p.store_id)
        FROM products p
        WHERE EXISTS (
            SELECT 1 FROM trusted_observations o
            WHERE o.provider = p.provider AND o.product_id = p.product_id AND o.store_id = p.store_id
        )
        {provider_sql}
        GROUP BY cat_name
        ORDER BY cat_name ASC
    ''', params)
    cats = [{"name": r[0], "products": r[1], "stores": r[2]} for r in c.fetchall()]
    conn.close()
    return cats
    
def get_stores(db_path, hide_empty=True, filters=None):
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    providers = (filters or {}).get("providers") or []
    query = '''
        SELECT s.provider, s.store_id, s.name, s.type, COUNT(p.product_id) as prod_count
        FROM stores s
        LEFT JOIN products p ON s.provider = p.provider AND s.store_id = p.store_id
    '''
    params = []
    if providers:
        query += f" WHERE s.provider IN ({','.join('?' for _ in providers)})"
        params.extend(providers)
    query += ' GROUP BY s.provider, s.store_id'
    if hide_empty:
        query += ' HAVING prod_count > 0'
    query += ' ORDER BY s.name ASC'
    
    c.execute(query, params)
    stores = [{"provider": r[0], "store_id": r[1], "name": r[2], "type": r[3], "products": r[4]} for r in c.fetchall()]
    conn.close()
    return stores

def get_store_detail(db_path, provider, store_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, type FROM stores WHERE provider = ? AND store_id = ?", (provider, store_id))
    row = c.fetchone()
    if not row:
        return None
    
    c.execute("SELECT COUNT(product_id) FROM products WHERE provider = ? AND store_id = ?", (provider, store_id))
    p_count = c.fetchone()[0]
    
    c.execute("SELECT MAX(timestamp) FROM trusted_observations WHERE provider = ? AND store_id = ?", (provider, store_id))
    last_obs = c.fetchone()[0]
    
    # categories
    c.execute('''
        SELECT COALESCE(NULLIF(TRIM(p.category), ''), 'Uncategorized') as cat_name, 
               COUNT(DISTINCT p.product_id)
        FROM products p
        WHERE p.provider = ? AND p.store_id = ?
        GROUP BY cat_name
        ORDER BY cat_name ASC
    ''', (provider, store_id))
    cats = [{"name": r[0], "count": r[1]} for r in c.fetchall()]
    
    conn.close()
    return {
        "provider": provider,
        "store_id": store_id,
        "name": row[0],
        "type": row[1],
        "products": p_count,
        "last_obs": last_obs,
        "categories": cats
    }


def get_restaurants_home(db_path, filters=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    providers = (filters or {}).get("providers") or []
    provider_sql = ""
    params = []
    if providers:
        provider_sql = f" AND s.provider IN ({','.join('?' for _ in providers)})"
        params.extend(providers)

    c.execute(f'''
        SELECT s.provider, s.store_id, s.name, s.brand,
               COUNT(DISTINCT p.product_id) as total_dishes,
               MAX(o.timestamp) as last_obs
        FROM stores s
        LEFT JOIN products p ON s.provider = p.provider AND s.store_id = p.store_id
        LEFT JOIN observations o ON p.provider = o.provider AND p.product_id = o.product_id AND p.store_id = o.store_id
        WHERE s.type = 'restaurants'
        {provider_sql}
        GROUP BY s.provider, s.store_id
        HAVING COUNT(DISTINCT p.product_id) > 0
        ORDER BY s.name ASC
    ''', params)
    
    stores = []
    for r in c.fetchall():
        provider = r[0]
        store_id = r[1]
        # Count available dishes
        c.execute('''
            SELECT COUNT(DISTINCT o.product_id)
            FROM trusted_observations o
            WHERE o.provider = ? AND o.store_id = ? AND o.availability = 'AVAILABLE'
            AND o.timestamp = (SELECT MAX(timestamp) FROM trusted_observations WHERE provider = o.provider AND product_id = o.product_id AND store_id = o.store_id)
        ''', (provider, store_id))
        available = c.fetchone()[0]
        
        # Count promotions
        c.execute('''
            SELECT COUNT(DISTINCT o.product_id)
            FROM trusted_observations o
            WHERE o.provider = ? AND o.store_id = ? AND o.discount_effective > 0
            AND o.timestamp = (SELECT MAX(timestamp) FROM trusted_observations WHERE provider = o.provider AND product_id = o.product_id AND store_id = o.store_id)
        ''', (provider, store_id))
        promos = c.fetchone()[0]
        
        stores.append({
            "provider": provider,
            "store_id": store_id,
            "name": r[2],
            "brand": r[3],
            "total_dishes": r[4],
            "available_dishes": available,
            "promos": promos,
            "last_obs": r[5]
        })
        
    conn.close()
    return stores

def get_restaurant_detail(db_path, provider, store_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT name, brand, type FROM stores WHERE provider = ? AND store_id = ? AND LOWER(type) IN ('restaurant', 'restaurants')", (provider, store_id,))
    row = c.fetchone()
    if not row:
        return None
        
    res = {
        "provider": provider,
        "store_id": store_id,
        "name": row[0],
        "brand": row[1],
        "type": row[2]
    }
    
    # Fetch menu items with their latest observations
    c.execute('''
        SELECT p.product_id, p.name, COALESCE(NULLIF(TRIM(p.category), ''), 'Otros') as category,
               o.price, o.original_price, o.discount_effective, o.promotion_label, o.promotion_type, o.availability,
               MAX(o.timestamp) as ts, p.has_toppings
        FROM products p
        JOIN observations o ON p.provider = o.provider AND p.product_id = o.product_id AND p.store_id = o.store_id
        WHERE p.provider = ? AND p.store_id = ?
        GROUP BY p.provider, p.product_id
        ORDER BY category ASC, p.name ASC
    ''', (provider, store_id))
    
    dishes = []
    cats = {}
    total_dishes = 0
    available_dishes = 0
    promos = 0
    
    for r in c.fetchall():
        total_dishes += 1
        is_avail = (r[8] == 'AVAILABLE')
        if is_avail:
            available_dishes += 1
        if r[5] and r[5] > 0:
            promos += 1
            
        dish = {
            "product_id": r[0],
            "name": r[1],
            "category": r[2],
            "price": r[3],
            "original_price": r[4],
            "discount_effective": r[5],
            "promotion_label": r[6],
            "promotion_type": r[7],
            "availability": r[8],
            "ts": r[9],
            "has_toppings": True if r[10] == 1 else (False if r[10] == 0 else None)
        }
            
        dishes.append(dish)
        
        if dish["category"] not in cats:
            cats[dish["category"]] = []
        cats[dish["category"]].append(dish)
        
    res["total_dishes"] = total_dishes
    res["available_dishes"] = available_dishes
    res["promos"] = promos
    res["categories"] = cats
    res["last_obs"] = dishes[0]["ts"] if dishes else None
    
    conn.close()
    return res


def search_local(db_path, query, filters=None):
    limit = 50
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    providers = (filters or {}).get("providers") or []

    # 1. Search Categories (using query_term or category field if it exists)
    c_results = []
    if query:
        provider_sql = ""
        params = [f"%{query}%"]
        if providers:
            provider_sql = f" AND provider IN ({','.join('?' for _ in providers)})"
            params.extend(providers)
        c.execute(f'''
            SELECT DISTINCT COALESCE(NULLIF(TRIM(category), ''), 'Uncategorized') as cat
            FROM products 
            WHERE cat LIKE ?
            {provider_sql}
            LIMIT 5
        ''', params)
        for r in c.fetchall():
            c_results.append({"name": r[0]})
            
    # 2. Search Stores
    s_results = []
    provider_sql = ""
    params = [f"%{query}%", f"%{query}%"]
    if providers:
        provider_sql = f" AND provider IN ({','.join('?' for _ in providers)})"
        params.extend(providers)
    c.execute(f'''
        SELECT provider, store_id, name, type, brand
        FROM stores
        WHERE (name LIKE ? OR brand LIKE ?)
        {provider_sql}
        LIMIT 10
    ''', params)
    for r in c.fetchall():
        s_results.append({
            "provider": r[0],
            "store_id": r[1],
            "name": r[2],
            "type": r[3],
            "brand": r[4]
        })
        
    # 3. Search Products (includes dishes)
    p_results = []
    query_str = f"SELECT p.provider, p.product_id, p.store_id, p.name, s.name, p.brand, s.type FROM products p JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id "
    params = []
    conditions = []
    if query:
        conditions.append("(p.name LIKE ? OR p.brand LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if providers:
        conditions.append(f"p.provider IN ({','.join('?' for _ in providers)})")
        params.extend(providers)
    if conditions:
        query_str += "WHERE " + " AND ".join(conditions) + " "
    query_str += f"LIMIT {limit}"
    
    c.execute(query_str, params)
    for r in c.fetchall():
        p_results.append({
            "provider": r[0],
            "product_id": r[1],
            "store_id": r[2],
            "name": r[3],
            "store_name": r[4],
            "brand": r[5],
            "store_type": r[6]
        })
        
    conn.close()
    return {
        "categories": c_results,
        "stores": s_results,
        "products": p_results
    }

def get_available_stores(db_path, vertical=None, filters=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    if vertical:
        if vertical == "turbo":
            c.execute("SELECT store_id, name FROM stores WHERE type IN ('chiper_home', 'chiper_extended', 'chiper_express') ORDER BY name")
        elif vertical == "market":
            c.execute("SELECT store_id, name FROM stores WHERE LOWER(type) NOT IN ('chiper_home', 'chiper_extended', 'chiper_express', 'restaurants', 'restaurant') ORDER BY name")
        else:
            c.execute("SELECT store_id, name FROM stores WHERE type = ? ORDER BY name", (vertical,))
    else:
        c.execute("SELECT store_id, name FROM stores ORDER BY name")
    return [{"id": r[0], "name": r[1]} for r in c.fetchall()]

def get_available_categories(db_path, vertical=None, store_ids=None, filters=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    query = "SELECT DISTINCT category FROM products p JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id WHERE category IS NOT NULL AND category != ''"
    params = []
    if vertical:
        if vertical == "turbo":
            query += " AND s.type IN ('chiper_home', 'chiper_extended', 'chiper_express')"
        elif vertical == "market":
            query += " AND s.LOWER(type) NOT IN ('chiper_home', 'chiper_extended', 'chiper_express', 'restaurants', 'restaurant')"
        else:
            query += " AND s.type = ?"
            params.append(vertical)
    
    if store_ids:
        placeholders = ",".join(["?"] * len(store_ids))
        query += f" AND p.store_id IN ({placeholders})"
        params.extend(store_ids)
        
    query += " ORDER BY category"
    c.execute(query, params)
    return [r[0] for r in c.fetchall()]


def _translate_filters(filters, sort=None, page=None, per_page=None):
    facets = {}
    if sort and page and per_page:
        offset = (page - 1) * per_page
        facets.update({
            "limit": per_page,
            "offset": offset,
            "sort": sort.replace("_asc", "").replace("_desc", "") if sort in ["price_asc", "price_desc", "name_asc"] else sort,
            "desc": "desc" in sort or sort in ["discount", "savings"]
        })
        if sort == "price_asc" or sort == "name_asc":
            facets["desc"] = False
    if filters.get("store"):
        store_values = filters["store"] if isinstance(filters["store"], list) else [filters["store"]]
        store_ids = []
        store_identities = []
        for value in store_values:
            if isinstance(value, str) and "::" in value:
                provider, store_id = value.split("::", 1)
                store_identities.append((provider, store_id))
            else:
                store_ids.append(value)
        if store_ids:
            facets["store_ids"] = store_ids
        if store_identities:
            facets["store_identities"] = store_identities
    providers = filters.get("providers")
    if not providers and filters.get("provider"):
        providers = [filters["provider"]]
    if providers:
        facets["providers"] = providers if isinstance(providers, list) else [providers]
    if filters.get("vertical"):
        v = filters["vertical"]
        if v == "turbo":
            facets["verticals"] = ["turbo", "chiper_home", "chiper_extended", "chiper_express"]
        elif v == "market":
            facets["verticals"] = ["market", "Supermercado", "Express", "Farmacias", "Mascotas", "Hogar"]
        else:
            facets["verticals"] = [v]
    if filters.get("category"):
        cats = filters["category"] if isinstance(filters["category"], list) else [filters["category"]]
        cats = [c for c in cats if c != "Uncategorized"]
        if cats:
            facets["categories"] = cats
    if filters.get("only_deals"):
        facets["min_discount"] = 1.0
    if filters.get("min_discount"):
        try:
            facets["min_discount"] = float(filters["min_discount"])
        except:
            pass
    if filters.get("channel"):
        facets["channel"] = filters["channel"]
    if filters.get("collections"):
        facets["collections"] = filters["collections"] if isinstance(filters["collections"], list) else [filters["collections"]]
    if filters.get("store_facets"):
        facets["store_facets"] = filters["store_facets"] if isinstance(filters["store_facets"], list) else [filters["store_facets"]]
    return facets

def get_ui_facets(db_path, filters):
    import sqlite3
    from dealhunter.query_layer import get_facet_counts
    from dealhunter.config import get_merged_config
    from dealhunter.config import get_merged_config
    conn = sqlite3.connect(db_path)
    facets = _translate_filters(filters)
    counts = get_facet_counts(conn, facets, get_merged_config(None))
    conn.close()
    return counts
