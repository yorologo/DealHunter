import sqlite3

def audit():
    conn = sqlite3.connect('/data/data/com.termux/files/home/rappi-deal-hunter/rappi-deals.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM stores")
    stores_total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM products")
    products_total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM observations")
    obs_total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM (SELECT store_id, product_id FROM observations GROUP BY store_id, product_id HAVING COUNT(*) > 1)")
    multi_obs = c.fetchone()[0]
    
    c.execute("SELECT MIN(timestamp), MAX(timestamp) FROM observations")
    min_ts, max_ts = c.fetchone()
    
    # Since crawler skips stock <= 0, all recorded observations are > 0.
    # However, let's just check the last observation for each product.
    c.execute("""
        SELECT COUNT(*) FROM (
            SELECT product_id, store_id, stock, ROW_NUMBER() OVER(PARTITION BY store_id, product_id ORDER BY timestamp DESC) as rn
            FROM observations
        ) WHERE rn = 1 AND stock > 0
    """)
    active_stock = c.fetchone()[0]
    
    c.execute("""
        SELECT COUNT(*) FROM (
            SELECT product_id, store_id, stock, ROW_NUMBER() OVER(PARTITION BY store_id, product_id ORDER BY timestamp DESC) as rn
            FROM observations
        ) WHERE rn = 1 AND stock <= 0
    """)
    no_stock = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM (SELECT store_id, product_id FROM observations WHERE discount_effective >= 50.0 GROUP BY store_id, product_id)")
    deals_50 = c.fetchone()[0]
    
    c.execute("SELECT s.type, COUNT(p.product_id) FROM products p JOIN stores s ON p.store_id = s.store_id GROUP BY s.type ORDER BY 2 DESC")
    dist_vertical = c.fetchall()
    
    c.execute("SELECT s.name, COUNT(p.product_id) FROM products p JOIN stores s ON p.store_id = s.store_id GROUP BY s.store_id ORDER BY 2 DESC LIMIT 15")
    dist_store = c.fetchall()
    
    c.execute("SELECT COUNT(DISTINCT name) FROM stores")
    unique_store_names = c.fetchone()[0]
    
    print("=== METRICAS BÁSICAS ===")
    print(f"Tiendas totales en SQLite: {stores_total}")
    print(f"Nombres únicos de tiendas: {unique_store_names}")
    print(f"Productos únicos totales: {products_total}")
    print(f"Observaciones totales: {obs_total}")
    print(f"Productos con >1 observación: {multi_obs}")
    print(f"Primera observación: {min_ts}")
    print(f"Última observación: {max_ts}")
    print(f"Productos activos/in_stock: {active_stock}")
    print(f"Productos actualmente sin stock: {no_stock}")
    print(f"Ofertas >=50% únicas: {deals_50}")
    
    print("\n=== DISTRIBUCIÓN POR VERTICAL (Basado en stores.type) ===")
    for v_type, count in dist_vertical:
        print(f"{v_type}: {count}")
        
    print("\n=== DISTRIBUCIÓN POR TIENDA (Top 15) ===")
    for s_name, count in dist_store:
        print(f"{s_name}: {count}")

if __name__ == '__main__':
    audit()
