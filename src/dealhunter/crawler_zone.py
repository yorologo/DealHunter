import time
import sys
import asyncio
from datetime import datetime
from .checkpoint import RunCheckpoint, save_checkpoint
from .catalog_sync import AuthenticatedHttpClient, MerchantDiscovery, CPGCatalogAdapter, RestaurantMenuAdapter, CoverageReport
from .auth import RappiSessionProvider
from .core import process_and_insert_product

def run_zone_inventory(config, lat, lng, conn, run_id, dry_run=False):
    return asyncio.run(_run_zone_inventory_async(config, lat, lng, conn, run_id, dry_run))

async def _run_zone_inventory_async(config, lat, lng, conn, run_id, dry_run=False):
    c = conn.cursor()
    seen_in_run = set()
    requests_count = 0
    start_time = time.time()
    
    checkpoint = RunCheckpoint(run_id=run_id, mode="zone_inventory", status="RUNNING")
    
    provider = RappiSessionProvider()
    if not await provider.is_authenticated():
        # Double check, shouldn't happen if router did its job
        return "SESSION_INVALID", 0
        
    client = AuthenticatedHttpClient(provider)
    discovery = MerchantDiscovery(client)
    cpg_adapter = CPGCatalogAdapter(client)
    rest_adapter = RestaurantMenuAdapter(client)
    
    report = CoverageReport()
    
    print("[*] Zone Inventory Mode started", file=sys.stderr)
    try:
        merchants = await discovery.discover_merchants(lat, lng, report)
    except Exception as e:
        if "401" in str(e):
            return "SESSION_EXPIRED", report.authenticated_requests
        raise e
        
    print(f"[*] Found {len(merchants)} merchants in zone", file=sys.stderr)
    
    global_state = "COMPLETED"
    
    # Store reconciliation:
    # First, mark all known stores as STALE temporarily? Wait, the prompt says:
    # "Si una tienda aparece en este run: last_seen_at = now, status = ACTIVE"
    # "Si una tienda conocida no aparece en un discovery COMPLETO: marcar como temporal/stale"
    
    # Let's get all known stores for this area? Or just mark all currently ACTIVE stores to UNKNOWN/STALE if they weren't seen?
    # Better: we know what we saw. 
    seen_store_ids = set()
    
    for idx, m in enumerate(merchants):
        if time.time() - start_time > config.get("max_runtime", 3600):
            global_state = "PARTIAL"
            break
            
        s_id = str(m.get("store_id", ""))
        s_name = m.get("name", "")
        seen_store_ids.add(s_id)
        
        c.execute('''INSERT INTO stores (store_id, name, brand, type, status, last_seen_at) 
                     VALUES (?, ?, ?, ?, ?, ?)
                     ON CONFLICT(store_id) DO UPDATE SET 
                     name = COALESCE(excluded.name, name), 
                     type = COALESCE(excluded.type, type),
                     status = 'ACTIVE',
                     last_seen_at = excluded.last_seen_at''',
                  (s_id, s_name, m.get("brand", ""), m.get("type", "supermercado"), "ACTIVE", datetime.now().isoformat()))
        conn.commit()
        
        if m.get("type") == "restaurant":
            if not config.get("restaurants", True):
                continue
            try:
                items = await rest_adapter.fetch_menu(s_id, report)
            except Exception as e:
                if "401" in str(e):
                    return "SESSION_EXPIRED", report.authenticated_requests
                continue
        else:
            try:
                items = await cpg_adapter.fetch_full_catalog(s_id, report)
            except Exception as e:
                if "401" in str(e):
                    return "SESSION_EXPIRED", report.authenticated_requests
                continue
                
        # Product reconciliation:
        # If catalog was fetched successfully, we can mark absent products as UNAVAILABLE.
        # items is a list of product dicts.
        seen_products_in_store = set()
        
        for p in items:
            if dry_run: continue
            pid = str(p.get("id") or p.get("product_id", ""))
            seen_products_in_store.add(pid)
            process_and_insert_product(p, run_id, s_id, s_name, config, "*", conn, seen_in_run)
            
        conn.commit()
        
        if not dry_run and items:
            # Mark products NOT seen in this store as UNAVAILABLE
            placeholders = ','.join(['?'] * len(seen_products_in_store))
            query = f'''
                SELECT product_id FROM products WHERE store_id = ? 
            '''
            c.execute(query, (s_id,))
            all_known = [row[0] for row in c.fetchall()]
            
            for kpid in all_known:
                if kpid not in seen_products_in_store:
                    # Mark unavailable in observations
                    c.execute('''INSERT OR IGNORE INTO observations 
                                 (run_id, store_id, product_id, price, original_price, stock, timestamp, 
                                 discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term, availability)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                 (run_id, s_id, kpid, 0, 0, 0, datetime.now().isoformat(), 
                                  0, 0, 0, "", "", "", "*", "UNAVAILABLE"))
            conn.commit()
            
        if not dry_run:
            time.sleep(2)
            
    # Stores not seen in a full discovery should be marked STALE
    if global_state == "COMPLETED" and not dry_run:
        c.execute('SELECT store_id FROM stores WHERE status = "ACTIVE"')
        for row in c.fetchall():
            if row[0] not in seen_store_ids:
                c.execute('UPDATE stores SET status = "STALE" WHERE store_id = ?', (row[0],))
        conn.commit()
        
    c.execute('''UPDATE runs SET crawler_mode = ?, coverage_complete = ?, finished_at = CURRENT_TIMESTAMP WHERE run_id = ?''', 
              ("ZONE_INVENTORY", 1 if global_state == "COMPLETED" else 0, run_id))
    conn.commit()
              
    return global_state, report.authenticated_requests
