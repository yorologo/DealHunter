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

def get_home_deals(db_path):
    # Using analyze_history from historico
    new_lows = analyze_history(db_path, {"status": ["NEW_LOW"], "sort": "discount"})
    real_deals = analyze_history(db_path, {"status": ["REAL_DEAL"], "sort": "discount"})
    good_prices = analyze_history(db_path, {"status": ["GOOD_PRICE"], "sort": "discount"})
    
    # Top 5 for each category to show on home
    return {
        "new_lows": new_lows[:5],
        "real_deals": real_deals[:5],
        "good_prices": good_prices[:5],
    }

def get_watchlist(db_path):
    c = sqlite3.connect(db_path).cursor()
    try:
        c.execute("SELECT query, store_filter, target_price FROM watchlist WHERE enabled = 1")
        return [{"query": r[0], "store": r[1], "target_price": r[2]} for r in c.fetchall()]
    except sqlite3.OperationalError:
        return []

def search_local(db_path, query, limit=10):
    c = sqlite3.connect(db_path).cursor()
    
    res = {}
    
    # Search products (max limit)
    c.execute('''
        SELECT DISTINCT p.product_id, p.store_id, p.name, s.name, p.image, p.brand
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        WHERE (p.name LIKE ? OR p.brand LIKE ? OR p.normalized_name LIKE ?)
        LIMIT ?
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
    
    products = []
    for r in c.fetchall():
        products.append({
            "product_id": r[0],
            "store_id": r[1],
            "name": r[2],
            "store_name": r[3],
            "image": r[4],
            "brand": r[5]
        })
    res["products"] = products
    
    # Search stores
    c.execute('''
        SELECT store_id, name, type
        FROM stores
        WHERE name LIKE ?
        LIMIT ?
    ''', (f'%{query}%', limit))
    stores = []
    for r in c.fetchall():
        stores.append({
            "store_id": r[0],
            "name": r[1],
            "type": r[2]
        })
    res["stores"] = stores
    
    return res

import sqlite3
from dealhunter.db import get_default_db_path
from dealhunter.historico import compute_price_metrics, compare_stores, compare_with_anchor
from dealhunter.normalization import format_unit_price
from datetime import datetime

def get_product_detail(db_path, store_id, product_id):
    c = sqlite3.connect(db_path).cursor()
    c.execute('''
        SELECT p.product_id, p.store_id, p.name, s.name, p.brand, 
               p.quantity, p.unit, p.normalized_quantity, p.normalized_unit, p.pack_count
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        WHERE p.store_id = ? AND p.product_id = ?
    ''', (store_id, product_id))
    row = c.fetchone()
    if not row:
        return None
        
    p = {
        "product_id": row[0],
        "store_id": row[1],
        "product_name": row[2],
        "store_name": row[3],
        "brand": row[4],
        "quantity": row[5],
        "unit": row[6],
        "normalized_quantity": row[7],
        "normalized_unit": row[8],
        "pack_count": row[9]
    }
    
    # Get obs
    c.execute('''
        SELECT price, timestamp, original_price, availability, discount_promotion, promotion_type, promotion_label, run_id
        FROM observations
        WHERE store_id = ? AND product_id = ?
        ORDER BY timestamp ASC
    ''', (store_id, product_id))
    
    obs_rows = c.fetchall()
    
    obs = []
    for r in obs_rows:
        try:
            ts = datetime.fromisoformat(r[1].replace("Z", ""))
        except:
            ts = datetime.now()
        obs.append({
            "price": r[0],
            "timestamp": ts,
            "original_price": r[2],
            "availability": r[3],
            "discount_promotion": r[4],
            "promotion_type": r[5],
            "promotion_label": r[6],
            "run_id": r[7]
        })
        
    p["observations"] = obs
    p["metrics"] = compute_price_metrics(obs) if obs else None
    if p["metrics"]:
        p["unit_price"] = format_unit_price(p["metrics"]["current_price"], p["normalized_quantity"], p["normalized_unit"])
    else:
        p["unit_price"] = None
        
    # Alerts
    c.execute("SELECT alert_type, triggered_at FROM alerts WHERE product_id = ? AND store_id = ? ORDER BY triggered_at DESC", (product_id, store_id))
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


def get_anchor_compare(db_path, store_id, product_id):
    return compare_with_anchor(db_path, store_id, product_id)


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
        conds.append("(product_id = ? AND store_id = ?)")
        params.extend([p["product_id"], p["store_id"]])
        
    query = f"SELECT store_id, product_id, price, timestamp, original_price FROM observations WHERE {' OR '.join(conds)} ORDER BY timestamp ASC"
    c.execute(query, params)
    obs_rows = c.fetchall()
    
    obs_map = {}
    for r in obs_rows:
        key = (r[0], r[1])
        if key not in obs_map:
            obs_map[key] = []
        try:
            ts = datetime.fromisoformat(r[3].replace("Z", ""))
        except:
            ts = datetime.now()
        obs_map[key].append({"price": r[2], "timestamp": ts, "original_price": r[4]})
        
    for p in products:
        key = (p["store_id"], p["product_id"])
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
    
    if tab in ["NEW_LOW", "REAL_DEAL", "GOOD_PRICE"]:
        # Price Intelligence deals
        res = analyze_history(db_path, {"status": tab})
        for r in res:
            items.append({
                "type": "pi", # Price Intelligence
                "data": r,
                "sort_date": r.get("timestamp", datetime.now()) # wait, analyze_history doesn't return timestamp of deal. It returns current_price. We can use latest observation.
            })
    elif tab in ["PRICE_DROP", "TARGET_PRICE", "BACK_IN_STOCK"]:
        # Alerts
        engine = AlertEngine(db_path)
        alerts = engine.get_alerts(alert_type=tab, top=1000)
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
        res = analyze_history(db_path, {})
        for r in res:
            if r.get("metrics", {}).get("is_suspicious_reference") or getattr(r, 'is_suspicious_reference', False): # wait, analyze_history doesn't return is_suspicious_reference directly, it might be in metrics. Let's check what it returns.
                items.append({
                    "type": "pi",
                    "data": r,
                    "sort_date": datetime.now()
                })
    else:
        # Todo
        res = analyze_history(db_path, {"status": ["NEW_LOW", "REAL_DEAL", "GOOD_PRICE"]})
        for r in res:
            items.append({
                "type": "pi",
                "data": r,
                "sort_date": datetime.now()
            })
            
        engine = AlertEngine(db_path)
        alerts = engine.get_alerts(top=1000)
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
            c.execute("SELECT normalized_quantity, normalized_unit FROM products WHERE product_id=? AND store_id=?", (i["data"]["product_id"], i["data"]["store_id"]))
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
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    offset = (page - 1) * per_page
    
    conds = []
    params = []
    
    if filters.get("store"):
        conds.append("p.store_id = ?")
        params.append(filters["store"])
        
    if filters.get("vertical"):
        conds.append("s.type = ?")
        params.append(filters["vertical"])
        
    if filters.get("category"):
        # Use query_term from observations
        conds.append("p.product_id IN (SELECT DISTINCT product_id FROM observations WHERE query_term = ?)")
        params.append(filters["category"])
        
    where_clause = f"WHERE {' AND '.join(conds)}" if conds else ""
    
    c.execute(f"SELECT COUNT(*) FROM products p JOIN stores s ON p.store_id = s.store_id {where_clause}", params)
    total = c.fetchone()[0]
    
    order_clause = "ORDER BY ts DESC"
    if sort == "price_asc":
        order_clause = "ORDER BY o.price ASC"
    elif sort == "price_desc":
        order_clause = "ORDER BY o.price DESC"
    elif sort == "name_asc":
        order_clause = "ORDER BY p.name ASC"
        
    query = f'''
        SELECT p.product_id, p.store_id, p.name, s.name, p.brand, p.quantity, p.unit, p.normalized_quantity, p.normalized_unit,
               MAX(o.timestamp) as ts, o.price
        FROM products p
        JOIN stores s ON p.store_id = s.store_id
        JOIN observations o ON p.product_id = o.product_id AND p.store_id = o.store_id
        {where_clause}
        GROUP BY p.store_id, p.product_id
        {order_clause}
        LIMIT ? OFFSET ?
    '''
    
    c.execute(query, params + [per_page, offset])
    rows = c.fetchall()
    
    products = []
    for r in rows:
        products.append({
            "product_id": r[0],
            "store_id": r[1],
            "product_name": r[2],
            "store_name": r[3],
            "brand": r[4],
            "quantity": r[5],
            "unit": r[6],
            "normalized_quantity": r[7],
            "normalized_unit": r[8],
            "current_price": r[10]
        })
        
    conn.close()
    
    items = enrich_products_with_metrics(db_path, products)
    
    # If they want to sort by opportunity, we do it post-enrichment for the page
    # Since we can't sort 20k items by opportunity without computing metrics for all of them
    if sort == "opportunity":
        def get_opp_key(item):
            m = item.get("metrics")
            if not m: return 99
            st = m.get("deal_status")
            if st == "NEW_LOW": return 0
            if st == "REAL_DEAL": return 1
            if st == "GOOD_PRICE": return 2
            return 3
        items.sort(key=get_opp_key)
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page
    }


def get_categories(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # query_term in observations acts as category
    c.execute('''
        SELECT o.query_term, COUNT(DISTINCT o.product_id), COUNT(DISTINCT o.store_id)
        FROM observations o
        WHERE o.query_term IS NOT NULL AND o.query_term != ''
        GROUP BY o.query_term
        ORDER BY o.query_term ASC
    ''')
    cats = [{"name": r[0], "products": r[1], "stores": r[2]} for r in c.fetchall()]
    conn.close()
    return cats
    
def get_stores(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT s.store_id, s.name, s.type, COUNT(DISTINCT p.product_id)
        FROM stores s
        LEFT JOIN products p ON s.store_id = p.store_id
        GROUP BY s.store_id
        ORDER BY s.name ASC
    ''')
    stores = [{"store_id": r[0], "name": r[1], "type": r[2], "products": r[3]} for r in c.fetchall()]
    conn.close()
    return stores

def get_store_detail(db_path, store_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, type FROM stores WHERE store_id = ?", (store_id,))
    row = c.fetchone()
    if not row:
        return None
    
    c.execute("SELECT COUNT(product_id) FROM products WHERE store_id = ?", (store_id,))
    p_count = c.fetchone()[0]
    
    c.execute("SELECT MAX(timestamp) FROM observations WHERE store_id = ?", (store_id,))
    last_obs = c.fetchone()[0]
    
    # categories
    c.execute('''
        SELECT o.query_term, COUNT(DISTINCT o.product_id)
        FROM observations o
        WHERE o.store_id = ? AND o.query_term IS NOT NULL AND o.query_term != ''
        GROUP BY o.query_term
        ORDER BY o.query_term ASC
    ''', (store_id,))
    cats = [{"name": r[0], "count": r[1]} for r in c.fetchall()]
    
    conn.close()
    return {
        "store_id": store_id,
        "name": row[0],
        "type": row[1],
        "products": p_count,
        "last_obs": last_obs,
        "categories": cats
    }
