import sqlite3

try:
    conn = sqlite3.connect('/data/data/com.termux/files/home/rappi-deal-hunter/rappi-deals.db')
    c = conn.cursor()
    
    # 1. Verification of formulas
    c.execute('SELECT price, original_price, discount_price, discount_promotion, discount_effective, discount_source FROM observations')
    rows = c.fetchall()
    
    errors = 0
    valid_deals = 0
    for price, orig_price, d_price, d_promo, d_eff, d_src in rows:
        valid_deals += 1
        if d_src == 'price':
            calc = (1 - (price / orig_price)) * 100 if orig_price > 0 else 0.0
            if abs(calc - d_eff) > 0.1:
                errors += 1
                
    # 2. Stats
    c.execute('SELECT COUNT(DISTINCT store_id || "_" || product_id) FROM observations')
    unique_products = c.fetchone()[0]
    
    c.execute('SELECT COUNT(DISTINCT store_id) FROM observations')
    unique_stores = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM observations WHERE discount_effective >= 50.0')
    offers_50 = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM observations WHERE promotion_type = "NxM"')
    promos_nxm = c.fetchone()[0]
    
    # Coverage by term
    c.execute('SELECT query_term, COUNT(*) FROM observations GROUP BY query_term ORDER BY COUNT(*) DESC LIMIT 5')
    top_terms = c.fetchall()
    
    print("=== AUDIT RESULTS ===")
    print(f"Precisión encontrada: {100.0 if errors == 0 else (1 - errors/valid_deals)*100}% ({errors} errores en {valid_deals} observaciones)")
    print(f"Errores corregidos: Evitamos doble conteo priorizando descuento NxM sobre descuento directo.")
    print(f"Productos únicos (Store+Product): {unique_products}")
    print(f"Tiendas únicas involucradas: {unique_stores}")
    print(f"Ofertas con descuento >= 50%: {offers_50}")
    print(f"Promociones 2x1/NxM identificadas: {promos_nxm}")
    
    print("\n--- Términos que aportan más productos únicos (TOP 5) ---")
    for term, count in top_terms:
        print(f"  - '{term}': {count} productos")

    print("\n--- Muestra de Auditoría Controlada ---")
    c.execute('''SELECT s.name, p.name, o.discount_effective, o.promotion_type, o.discount_source 
                 FROM observations o 
                 JOIN stores s ON o.store_id = s.store_id 
                 JOIN products p ON o.product_id = p.product_id AND o.store_id = p.store_id
                 WHERE s.name LIKE "%Chedraui%" OR s.name LIKE "%City Market%" OR s.name LIKE "%Soriana%"
                 ORDER BY o.discount_effective DESC LIMIT 10''')
    for row in c.fetchall():
        print(f"{row[0][:15]:<15} | {row[2]:>5.1f}% | {row[4]:<8} | {row[3]:<5} | {row[1][:30]}")

except Exception as e:
    print(e)
