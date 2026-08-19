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
from dealhunter.historico import compute_price_metrics, calculate_unit_price, compare_stores, compare_with_anchor
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
        p["unit_price"] = calculate_unit_price(p["metrics"]["current_price"], p["normalized_quantity"])
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
