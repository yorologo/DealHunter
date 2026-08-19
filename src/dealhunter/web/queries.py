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
        WHERE p.name LIKE ? OR p.brand LIKE ? OR p.normalized_name LIKE ?
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

