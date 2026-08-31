import sqlite3
import subprocess
import json

def matches_canary_watch(ev):
    t = ev['event_type']
    meta = ev.get('metadata', {})
    
    if t in ('NEW_DEAL', 'NEW_PRODUCT_WITH_DEAL'):
        after_val = ev.get('after_value')
        try:
            if after_val and float(after_val) >= 50.0:
                return True
        except ValueError:
            pass
            
    elif t == 'NXM_APPEARED':
        # Send NxM (e.g., 2x1, 3x2)
        return True
        
    elif t == 'PRO_DEAL_APPEARED':
        pro_discount = meta.get('pro_discount_effective')
        if pro_discount is not None:
            try:
                if float(pro_discount) >= 50.0:
                    return True
            except ValueError:
                pass
                
    elif t == 'PROGRESSIVE_APPEARED':
        after_val = ev.get('after_value')
        # If we have an effective discount known and >= 50
        # For progressive, usually 'after_value' is the string 'Progressive', so we might not have discount here
        # Let's check metadata if there is a discount
        # If not, let's just suppress it for now to be safe, or allow it if the string contains a big discount
        pass

    return False

def format_event(ev, db_cursor=None):
    t = ev['event_type']
    meta = ev.get('metadata', {})
    provider = ev.get('provider', 'rappi')
    
    # Try to get product info for better formatting
    product_name = ev['product_id']
    store_name = ev['store_id']
    if db_cursor:
        try:
            db_cursor.execute(
                "SELECT name FROM products WHERE provider = ? AND product_id = ? AND store_id = ?",
                (provider, ev['product_id'], ev['store_id']),
            )
            p_row = db_cursor.fetchone()
            if p_row: product_name = p_row[0]
            
            db_cursor.execute(
                "SELECT name FROM stores WHERE provider = ? AND store_id = ?",
                (provider, ev['store_id']),
            )
            s_row = db_cursor.fetchone()
            if s_row: store_name = s_row[0]
        except Exception:
            pass
            
    if t in ('NEW_DEAL', 'NEW_PRODUCT_WITH_DEAL'):
        disc = ev.get('after_value', '??')
        # We need original price and current price for "$100 -> $45"
        # We don't have it directly in 'after_value', but we can try to fetch it from current_observation_id
        price_str = ""
        if db_cursor and ev.get('current_observation_id'):
            try:
                db_cursor.execute("SELECT original_price, price FROM trusted_observations WHERE id = ?", (ev['current_observation_id'],))
                obs_row = db_cursor.fetchone()
                if obs_row and obs_row[0] and obs_row[1]:
                    price_str = f" · ${obs_row[0]} → ${obs_row[1]}"
            except Exception:
                pass
        return f"🔥 {disc}% — {product_name}\n{store_name}{price_str}"
        
    elif t == 'NXM_APPEARED':
        promo = ev.get('after_value', 'Promo')
        return f"🎁 {promo} — {product_name}\n{store_name}"
        
    elif t == 'PRO_DEAL_APPEARED':
        disc = meta.get('pro_discount_effective', '??')
        pro_price = meta.get('pro_price', '??')
        return f"🟣 Pro {disc}% — {product_name}\n{store_name} · ${pro_price} con Pro"
        
    elif t == 'PRICE_DROP':
        drop = meta.get('drop_pct', 0)
        return f"⬇️ {product_name} bajó {drop:.1f}%: {ev['before_value']} → {ev['after_value']}"
        
    elif t == 'BACK_IN_STOCK':
        return f"✅ {product_name} volvió a estar disponible"
        
    return f"ℹ️ {t} en {product_name}"

def send_pending_events(db_path, limit=5, dry_run=False):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute("SELECT id, provider, event_type, store_id, product_id, before_value, after_value, metadata, current_observation_id FROM alert_events WHERE delivery_status = 'pending' ORDER BY created_at ASC")
    rows = c.fetchall()
    
    delivered_count = 0
    
    for r in rows:
        ev = {
            'id': r[0],
            'provider': r[1],
            'event_type': r[2],
            'store_id': r[3],
            'product_id': r[4],
            'before_value': r[5],
            'after_value': r[6],
            'metadata': json.loads(r[7]) if r[7] else {},
            'current_observation_id': r[8]
        }
        
        if not matches_canary_watch(ev):
            c.execute("UPDATE alert_events SET delivery_status = 'suppressed' WHERE id = ?", (ev['id'],))
            continue
            
        if delivered_count >= limit:
            continue
            
        msg = format_event(ev, c)
        
        if dry_run:
            print("DRY RUN Notification:")
            print(msg)
            print("---")
            delivered_count += 1
            c.execute("UPDATE alert_events SET delivery_status = 'sent' WHERE id = ?", (ev['id'],))
            continue
            
        try:
            res = subprocess.run([
                "termux-notification", 
                "--title", "DealHunter",
                "--content", msg
            ], capture_output=True, timeout=5)
            
            if res.returncode == 0:
                c.execute("UPDATE alert_events SET delivery_status = 'sent' WHERE id = ?", (ev['id'],))
                delivered_count += 1
            else:
                c.execute("UPDATE alert_events SET delivery_status = 'failed' WHERE id = ?", (ev['id'],))
        except Exception as e:
            c.execute("UPDATE alert_events SET delivery_status = 'failed' WHERE id = ?", (ev['id'],))
            
    conn.commit()
    conn.close()
    
if __name__ == '__main__':
    # For testing Termux delivery directly
    send_pending_events("rappi-deals.db", limit=1)
