with open("src/dealhunter/db.py", "r") as f:
    content = f.read()
    
# Fix v10 migration
old_10 = """
        if version < 10:
            c.execute("ALTER TABLE stores ADD COLUMN vertical TEXT")
"""
new_10 = """
        if version < 10:
            try:
                c.execute("ALTER TABLE stores ADD COLUMN vertical TEXT")
            except sqlite3.OperationalError:
                pass
"""
content = content.replace(old_10, new_10)

# Also fix the duplicate provider issue in v15
old_15 = """
        if version < 15:
            # Multi-provider Schema v15
            
            # STORES
            c.execute('''CREATE TABLE stores_v15 (
                provider TEXT DEFAULT 'rappi', store_id TEXT, name TEXT, brand TEXT, type TEXT, status TEXT DEFAULT 'UNKNOWN', last_seen_at DATETIME, vertical TEXT, PRIMARY KEY(provider, store_id)
            )''')
            c.execute('''INSERT INTO stores_v15 (provider, store_id, name, brand, type, status, last_seen_at, vertical)
                         SELECT 'rappi', store_id, name, brand, type, status, last_seen_at, vertical FROM stores''')
            c.execute('DROP TABLE stores')
            c.execute('ALTER TABLE stores_v15 RENAME TO stores')
            
            # PRODUCTS
            c.execute('''CREATE TABLE products_v15 (
                provider TEXT DEFAULT 'rappi', product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, 
                normalized_name TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, 
                fingerprint TEXT, pack_count INTEGER, category TEXT, has_toppings INTEGER, category_source TEXT DEFAULT 'unknown',
                PRIMARY KEY (provider, store_id, product_id)
            )''')
            c.execute('''INSERT INTO products_v15 (
                provider, product_id, store_id, name, brand, image, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count, category, has_toppings, category_source
            ) SELECT 'rappi', product_id, store_id, name, brand, image, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count, category, has_toppings, category_source FROM products''')
            c.execute('DROP TABLE products')
            c.execute('ALTER TABLE products_v15 RENAME TO products')
            
            # OBSERVATIONS
            c.execute('''CREATE TABLE observations_v15 (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, provider TEXT DEFAULT 'rappi', store_id TEXT, product_id TEXT, 
                price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, 
                discount_price REAL, discount_promotion REAL, discount_effective REAL, 
                discount_source TEXT, promotion_type TEXT, promotion_label TEXT, 
                query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT NULL, pro_price REAL, pro_discount_effective REAL, limit_info TEXT, UNIQUE(run_id, provider, store_id, product_id)
            )''')
            c.execute('''INSERT INTO observations_v15 (
                id, run_id, provider, store_id, product_id, price, original_price, stock, timestamp, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term, availability, has_pro_offer, pro_price, pro_discount_effective, limit_info
            ) SELECT id, run_id, 'rappi', store_id, product_id, price, original_price, stock, timestamp, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term, availability, has_pro_offer, pro_price, pro_discount_effective, limit_info FROM observations''')
            c.execute('DROP TABLE observations')
            c.execute('ALTER TABLE observations_v15 RENAME TO observations')
            
            # FACETS
            c.execute('''CREATE TABLE store_facets_v15 (
                provider TEXT DEFAULT 'rappi', store_id TEXT NOT NULL, facet_type TEXT NOT NULL, raw_value TEXT NOT NULL, source TEXT, last_seen DATETIME, UNIQUE(provider, store_id, facet_type, raw_value)
            )''')
            c.execute('''INSERT INTO store_facets_v15 (provider, store_id, facet_type, raw_value, source, last_seen)
                         SELECT 'rappi', store_id, facet_type, raw_value, source, last_seen FROM store_facets''')
            c.execute('DROP TABLE store_facets')
            c.execute('ALTER TABLE store_facets_v15 RENAME TO store_facets')
"""
new_15 = """
        if version < 15:
            try:
                # We only need to migrate if the old schema exists (i.e. if provider doesn't exist yet)
                c.execute("SELECT provider FROM stores LIMIT 1")
            except sqlite3.OperationalError:
                # STORES
                c.execute('''CREATE TABLE stores_v15 (
                    provider TEXT DEFAULT 'rappi', store_id TEXT, name TEXT, brand TEXT, type TEXT, status TEXT DEFAULT 'UNKNOWN', last_seen_at DATETIME, vertical TEXT, PRIMARY KEY(provider, store_id)
                )''')
                c.execute('''INSERT INTO stores_v15 (provider, store_id, name, brand, type, status, last_seen_at, vertical)
                             SELECT 'rappi', store_id, name, brand, type, status, last_seen_at, vertical FROM stores''')
                c.execute('DROP TABLE stores')
                c.execute('ALTER TABLE stores_v15 RENAME TO stores')
                
                # PRODUCTS
                c.execute('''CREATE TABLE products_v15 (
                    provider TEXT DEFAULT 'rappi', product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, 
                    normalized_name TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, 
                    fingerprint TEXT, pack_count INTEGER, category TEXT, has_toppings INTEGER, category_source TEXT DEFAULT 'unknown',
                    PRIMARY KEY (provider, store_id, product_id)
                )''')
                c.execute('''INSERT INTO products_v15 (
                    provider, product_id, store_id, name, brand, image, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count, category, has_toppings, category_source
                ) SELECT 'rappi', product_id, store_id, name, brand, image, normalized_name, quantity, unit, normalized_quantity, normalized_unit, fingerprint, pack_count, category, has_toppings, category_source FROM products''')
                c.execute('DROP TABLE products')
                c.execute('ALTER TABLE products_v15 RENAME TO products')
                
                # OBSERVATIONS
                c.execute('''CREATE TABLE observations_v15 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, provider TEXT DEFAULT 'rappi', store_id TEXT, product_id TEXT, 
                    price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, 
                    discount_price REAL, discount_promotion REAL, discount_effective REAL, 
                    discount_source TEXT, promotion_type TEXT, promotion_label TEXT, 
                    query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT NULL, pro_price REAL, pro_discount_effective REAL, limit_info TEXT, UNIQUE(run_id, provider, store_id, product_id)
                )''')
                c.execute('''INSERT INTO observations_v15 (
                    id, run_id, provider, store_id, product_id, price, original_price, stock, timestamp, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term, availability, has_pro_offer, pro_price, pro_discount_effective, limit_info
                ) SELECT id, run_id, 'rappi', store_id, product_id, price, original_price, stock, timestamp, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term, availability, has_pro_offer, pro_price, pro_discount_effective, limit_info FROM observations''')
                c.execute('DROP TABLE observations')
                c.execute('ALTER TABLE observations_v15 RENAME TO observations')
                
                # FACETS
                c.execute('''CREATE TABLE store_facets_v15 (
                    provider TEXT DEFAULT 'rappi', store_id TEXT NOT NULL, facet_type TEXT NOT NULL, raw_value TEXT NOT NULL, source TEXT, last_seen DATETIME, UNIQUE(provider, store_id, facet_type, raw_value)
                )''')
                c.execute('''INSERT INTO store_facets_v15 (provider, store_id, facet_type, raw_value, source, last_seen)
                             SELECT 'rappi', store_id, facet_type, raw_value, source, last_seen FROM store_facets''')
                c.execute('DROP TABLE store_facets')
                c.execute('ALTER TABLE store_facets_v15 RENAME TO store_facets')
"""
content = content.replace(old_15, new_15)

with open("src/dealhunter/db.py", "w") as f:
    f.write(content)
