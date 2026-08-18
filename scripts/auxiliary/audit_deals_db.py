import sqlite3

def audit_deals():
    conn = sqlite3.connect('/data/data/com.termux/files/home/rappi-deal-hunter/rappi-deals.db')
    c = conn.cursor()
    
    c.execute('''SELECT o.product_id, p.name, s.name, o.price, o.original_price, 
                        o.discount_price, o.discount_promotion, o.discount_effective, 
                        o.discount_source, o.promotion_label, o.promotion_type
                 FROM observations o
                 JOIN products p ON o.product_id = p.product_id AND o.store_id = p.store_id
                 JOIN stores s ON o.store_id = s.store_id
                 WHERE o.discount_effective >= 50.0''')
    rows = c.fetchall()
    
    print("--- AUDITORIA OFERTAS >= 50% ---")
    falsas = 0
    validas = 0
    for r in rows:
        prod_id, p_name, s_name, price, orig_price, d_price, d_promo, d_eff, d_src, p_label, p_type = r
        
        # parse units and value from label if possible
        # Rappi labels: "Agregue X, pague Y"
        units = 0
        p_val = 0
        if "Agregue " in str(p_label):
            try:
                parts = p_label.replace("Agregue ", "").split(", pague ")
                p_val = float(parts[0])
                units = float(parts[1])
            except:
                pass
                
        is_false = False
        # double check logic
        if p_type == 'NxM' and p_val > 0 and units > 0:
            calc_promo = (1 - (units / p_val)) * 100
            if abs(calc_promo - d_promo) > 1.0:
                is_false = True
            if calc_promo < 50.0 and d_eff >= 50.0:
                is_false = True
                
        if d_eff > max(d_price, d_promo):
            is_false = True
            
        print(f"Producto: {p_name}")
        print(f"Tienda: {s_name}")
        print(f"Precio: {price} | Original: {orig_price}")
        print(f"Discount Price: {d_price:.2f}% | Discount Promo: {d_promo:.2f}%")
        print(f"Promo Text: {p_label} | Units_condition: {units} | Prom_value: {p_val}")
        print(f"Discount Effective: {d_eff:.2f}% | Source: {d_src}")
        if is_false:
            print(">>> CLASIFICACION INCORRECTA DETECTADA")
            falsas += 1
            # Auto-correct in DB
            c.execute('UPDATE observations SET discount_effective = ? WHERE product_id = ?', (max(d_price, d_promo), prod_id))
        else:
            print(">>> CLASIFICACION CORRECTA")
            validas += 1
        print("-" * 50)
        
    conn.commit()
    print(f"Ofertas >=50% antes: {len(rows)}")
    print(f"Falsas eliminadas: {falsas}")
    print(f"Ofertas >=50% finales: {validas}")

if __name__ == '__main__':
    audit_deals()
