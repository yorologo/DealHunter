import asyncio
import json
import time
import os
import sqlite3
from dealhunter.db import setup_db, get_default_db_path
from dealhunter.providers.uber_eats.browser_transport import UberBrowserTransport
from dealhunter.providers.uber_eats.parser import UberEatsParser
from dealhunter.providers.uber_eats.normalizer import UberEatsNormalizer
from dealhunter.core import process_and_insert_product

os.environ["DEALHUNTER_DB_PATH"] = os.path.expanduser("~/.config/dealhunter/uber_test.sqlite")
DB_PATH = get_default_db_path()
setup_db(DB_PATH)

STORES = [
    ("Tony Pepperoni", "832b0757-ca82-4b62-8232-c1b615a6d22d", "RESTAURANT"),
    ("Da Fabio Trattoria Pizzeria Bar", "03521919-0ef9-4f94-94c7-39bdfa126298", "RESTAURANT"),
    ("Pizzahead", "d3fa2538-6e34-49d4-a6ec-0cb484918bc7", "RESTAURANT"),
    ("7-Eleven", "72bb4dc4-18d4-636d-9ea4-bf9d2fbe0000", "GROCERY"),
    ("OXXO", "95d42fe0-a4ad-5d80-b371-9fb3a428e124", "GROCERY"),
]

async def main():
    transport = UberBrowserTransport()
    parser = UberEatsParser()
    normalizer = UberEatsNormalizer()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    run_id = int(time.time())
    
    c.execute('''
        INSERT INTO runs (
            run_id, lat, lng, 
            status, started_at
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        run_id, 0.0, 0.0,
        'RUNNING', time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
    ))
    conn.commit()
    
    try:
        await transport.connect()
    except Exception as e:
        print("Failed to connect:", e)
        return

    # Mock config and Queue for process_and_insert_product
    config = {'min_discount': 0}
    
    for name, uuid_str, type_ in STORES:
        print(f"\n--- Syncing {name} ({uuid_str}) ---")
        try:
            res = await transport.capture_store(uuid_str, max_pages=15)
            
            if res.get("status") != "empty" and res.get("completeness") != "FAILED":
                parsed = parser.parse_store(res.get("raw_payload", {}))
                products = parsed.get("products", [])
                
                print(f"Captured {len(products)} products")
                
                # Insert store manually
                c.execute('''INSERT OR IGNORE INTO stores (provider, store_id, name, type)
                             VALUES (?, ?, ?, ?)''', ('uber_eats', uuid_str, name, type_))
                             
                obs_count = 0
                seen_in_run = set()
                
                for prod in products:
                    n_prod = normalizer.normalize_product(prod)
                    n_obs = normalizer.normalize_observation(prod, run_id)
                    n_prod["provider"] = "uber_eats"
                    n_obs["provider"] = "uber_eats"
                    
                    # We can use process_and_insert_product which handles the complex logic
                    # wait, n_prod doesn't exactly match Rappi. 
                    # process_and_insert_product expects Rappi dict format!
                    # So let's insert it manually!
                    c.execute('''INSERT INTO products (provider, product_id, store_id, name, brand, image, category)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                 ON CONFLICT(provider, store_id, product_id) DO UPDATE SET
                                 name=excluded.name, brand=excluded.brand, image=excluded.image,
                                 category=excluded.category''',
                              ('uber_eats', n_prod["product_id"], n_prod["store_id"], n_prod["name"], 
                               n_prod.get("brand", ""), n_prod.get("image", ""), n_prod.get("category", "")))
                               
                    c.execute('''INSERT INTO observations (
                                    run_id, provider, store_id, product_id,
                                    price, original_price, discount_price, 
                                    discount_promotion, discount_effective,
                                    promotion_type, stock
                                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (n_obs["run_id"], 'uber_eats', n_obs["store_id"], n_obs["product_id"],
                               n_obs["price"], n_obs["original_price"], n_obs["discount_price"],
                               n_obs["discount_promotion"], n_obs["discount_effective"],
                               n_obs.get("promotion_type", ""), n_obs["stock"]))
                    obs_count += 1
                
                conn.commit()
                print(f"Persisted {obs_count} observations to DB.")
                
            else:
                print(f"Failed to capture {name}: {res.get('status')} {res.get('completeness')}")
                
        except Exception as e:
            print(f"Error capturing {name}: {e}")
            import traceback
            traceback.print_exc()

    c.execute('UPDATE runs SET status = ?, finished_at = ? WHERE run_id = ?', 
              ('SUCCESS', time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime()), run_id))
    conn.commit()
    print("\nDONE!")
        
asyncio.run(main())
