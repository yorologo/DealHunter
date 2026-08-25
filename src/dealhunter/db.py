import sqlite3
import os
import datetime
import shutil
import sys

CURRENT_SCHEMA_VERSION = 15

def get_default_db_path():
    return os.environ.get("RAPPI_DB_PATH", os.path.expanduser("~/rappi-deal-hunter/rappi-deals.db"))

def setup_db(db_path=None):
    if not db_path:
        db_path = get_default_db_path()
    
    conn = sqlite3.connect(db_path)
    
    # Ensure backward compatibility by creating existing tables if they don't exist
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stores
                 (provider TEXT NOT NULL DEFAULT 'rappi', store_id TEXT, name TEXT, brand TEXT, type TEXT,
                  PRIMARY KEY (provider, store_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (provider TEXT NOT NULL DEFAULT 'rappi', product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
                  normalized_name TEXT, quantity REAL, unit TEXT, 
                  normalized_quantity REAL, normalized_unit TEXT, fingerprint TEXT,
                  pack_count INTEGER,
                  category TEXT,
                  has_toppings INTEGER,
                  category_source TEXT DEFAULT 'unknown',
                  PRIMARY KEY (provider, store_id, product_id))''')
                  
    c.execute('''CREATE TABLE IF NOT EXISTS runs (
                 run_id TEXT PRIMARY KEY, 
                 started_at DATETIME, 
                 finished_at DATETIME, 
                 lat REAL, 
                 lng REAL, 
                 radius REAL, 
                 vertical TEXT, 
                 status TEXT)''')
                 
    # Base creation logic for v2
    c.execute('''CREATE TABLE IF NOT EXISTS observations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, provider TEXT NOT NULL DEFAULT 'rappi', store_id TEXT, product_id TEXT, 
                  price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, 
                  discount_price REAL, discount_promotion REAL, discount_effective REAL,
                  discount_source TEXT, promotion_type TEXT, promotion_label TEXT,
                  query_term TEXT, availability TEXT,
                  UNIQUE(run_id, provider, store_id, product_id))''')

    # Migrations
    migrate(conn, db_path)
    
    return conn

def migrate(conn, db_path):
    c = conn.cursor()
    
    # Check current version
    c.execute('''CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)''')
    c.execute('SELECT version FROM schema_version LIMIT 1')
    row = c.fetchone()
    if row is None:
        version = 0
        c.execute('INSERT INTO schema_version (version) VALUES (0)')
    else:
        version = row[0]
        
    if version < CURRENT_SCHEMA_VERSION:
        # Create a backup before migration
        backup_db(db_path, tag="pre_migration")
        
        # apply migrations
        if version < 1:
            c.execute('''CREATE TABLE IF NOT EXISTS watchlist (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         query TEXT,
                         store_filter TEXT,
                         target_price REAL,
                         min_discount REAL,
                         created_at DATETIME,
                         enabled INTEGER DEFAULT 1)''')
                         
        if version < 2:
            try:
                c.execute('''ALTER TABLE observations ADD COLUMN availability TEXT''')
            except sqlite3.OperationalError:
                pass # Column might exist if creating from scratch using v2 string above
                
        if version < 3:
            cols = ["normalized_name TEXT", "quantity REAL", "unit TEXT", 
                    "normalized_quantity REAL", "normalized_unit TEXT", "fingerprint TEXT"]
            for col in cols:
                try:
                    c.execute(f"ALTER TABLE products ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass

        if version < 4:
            try:
                c.execute("ALTER TABLE products ADD COLUMN pack_count INTEGER")
            except sqlite3.OperationalError:
                pass
                

        if version < 5:
            c.execute('''CREATE TABLE IF NOT EXISTS alerts (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         provider TEXT NOT NULL DEFAULT 'rappi',
                         product_id TEXT,
                         store_id TEXT,
                         alert_type TEXT,
                         triggered_at DATETIME,
                         price REAL,
                         previous_price REAL,
                         deal_status TEXT,
                         reason TEXT,
                         seen INTEGER DEFAULT 0,
                         UNIQUE(provider, product_id, store_id, alert_type, price)
                         )''')
        
        if version < 6:
            try:
                c.execute("ALTER TABLE products ADD COLUMN category TEXT")
            except sqlite3.OperationalError:
                pass
                
        if version < 7:
            try:
                c.execute("ALTER TABLE products ADD COLUMN has_toppings INTEGER")
                c.execute("ALTER TABLE products ADD COLUMN category_source TEXT DEFAULT 'unknown'")
            except sqlite3.OperationalError:
                pass
        # update version


        if version < 8:
            try:
                c.execute("ALTER TABLE stores ADD COLUMN status TEXT DEFAULT 'UNKNOWN'")
            except Exception: pass
            try:
                c.execute("ALTER TABLE stores ADD COLUMN last_seen_at DATETIME")
            except Exception: pass
            try:
                c.execute("ALTER TABLE runs ADD COLUMN crawler_mode TEXT")
            except Exception: pass
            try:
                c.execute("ALTER TABLE runs ADD COLUMN coverage_complete INTEGER DEFAULT 0")
            except Exception: pass
                
        if version < 9:
            try:
                c.execute("ALTER TABLE runs ADD COLUMN run_metadata TEXT")
            except Exception: pass
            try:
                c.execute("ALTER TABLE runs ADD COLUMN source TEXT DEFAULT 'CLI'")
            except Exception: pass

        if version < 10:
            try:
                c.execute("ALTER TABLE stores ADD COLUMN vertical TEXT")
            except Exception: pass
            c.execute('''CREATE TABLE IF NOT EXISTS store_facets (
                provider TEXT NOT NULL DEFAULT 'rappi',
                store_id TEXT NOT NULL,
                facet_type TEXT NOT NULL,
                raw_value TEXT NOT NULL,
                source TEXT,
                last_seen DATETIME,
                UNIQUE(provider, store_id, facet_type, raw_value)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS product_memberships (
                provider TEXT NOT NULL DEFAULT 'rappi',
                store_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                raw_type TEXT,
                raw_name TEXT NOT NULL,
                raw_id TEXT,
                path TEXT,
                source TEXT,
                last_seen DATETIME,
                semantic_type TEXT DEFAULT 'UNKNOWN',
                semantic_reason TEXT DEFAULT 'not_classified',
                UNIQUE(provider, store_id, product_id, raw_type, raw_name, path)
            )''')


        if version < 11:
            try:
                c.execute("ALTER TABLE product_memberships ADD COLUMN semantic_type TEXT DEFAULT 'UNKNOWN'")
                c.execute("ALTER TABLE product_memberships ADD COLUMN semantic_reason TEXT DEFAULT 'not_classified'")
            except sqlite3.OperationalError:
                pass # Already exists

        if version < 12:
            c.execute("ALTER TABLE observations ADD COLUMN has_pro_offer INTEGER DEFAULT NULL")
            c.execute("ALTER TABLE observations ADD COLUMN pro_price REAL")
            c.execute("ALTER TABLE observations ADD COLUMN pro_discount_effective REAL")
            c.execute("ALTER TABLE observations ADD COLUMN limit_info TEXT")


        if version < 13:
            try:
                c.execute('CREATE INDEX IF NOT EXISTS idx_obs_history ON observations(store_id, product_id, timestamp DESC, id DESC)')
            except sqlite3.OperationalError:
                pass
                
        if version < 14:
            c.execute('''CREATE TABLE IF NOT EXISTS alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT UNIQUE NOT NULL,
                provider TEXT NOT NULL DEFAULT 'rappi',
                event_type TEXT NOT NULL,
                store_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                previous_observation_id INTEGER,
                current_observation_id INTEGER,
                channel TEXT NOT NULL,
                before_value TEXT,
                after_value TEXT,
                metadata TEXT,
                created_at DATETIME NOT NULL,
                delivery_status TEXT DEFAULT 'pending'
            )''')

        
        if version < 15:
            def table_exists(t):
                c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
                return c.fetchone() is not None

            def get_cols(t):
                c.execute(f"PRAGMA table_info({t})")
                return [row[1] for row in c.fetchall()]

            def migrate_table(old_name, new_ddl):
                if not table_exists(old_name): return
                new_name = f"_{old_name}_new"
                c.execute(new_ddl)
                
                # Get existing columns in old table
                old_cols = get_cols(old_name)
                # Get columns in new table
                new_cols = get_cols(new_name)
                
                # Intersection
                common_cols = [col for col in old_cols if col in new_cols]
                
                if common_cols:
                    cols_str = ", ".join(common_cols)
                    c.execute(f"INSERT INTO {new_name} ({cols_str}) SELECT {cols_str} FROM {old_name}")
                
                c.execute(f"DROP TABLE {old_name}")
                c.execute(f"ALTER TABLE {new_name} RENAME TO {old_name}")

            # STORES
            migrate_table('stores', "CREATE TABLE _stores_new (provider TEXT NOT NULL DEFAULT 'rappi', store_id TEXT, name TEXT, brand TEXT, type TEXT, status TEXT DEFAULT 'UNKNOWN', last_seen_at DATETIME, vertical TEXT, PRIMARY KEY (provider, store_id))")

            # PRODUCTS
            migrate_table('products', """CREATE TABLE _products_new (
                  provider TEXT NOT NULL DEFAULT 'rappi', product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
                  normalized_name TEXT, quantity REAL, unit TEXT, 
                  normalized_quantity REAL, normalized_unit TEXT, fingerprint TEXT,
                  pack_count INTEGER, category TEXT, has_toppings INTEGER, category_source TEXT DEFAULT 'unknown',
                  PRIMARY KEY (provider, store_id, product_id))""")

            # OBSERVATIONS
            migrate_table('observations', """CREATE TABLE _observations_new (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, provider TEXT NOT NULL DEFAULT 'rappi', store_id TEXT, product_id TEXT, 
                  price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, 
                  discount_price REAL, discount_promotion REAL, discount_effective REAL,
                  discount_source TEXT, promotion_type TEXT, promotion_label TEXT,
                  query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT NULL,
                  pro_price REAL, pro_discount_effective REAL, limit_info TEXT,
                  UNIQUE(run_id, provider, store_id, product_id))""")
            
            try:
                c.execute('CREATE INDEX IF NOT EXISTS idx_obs_history ON observations(provider, store_id, product_id, timestamp DESC, id DESC)')
                c.execute('DROP INDEX IF EXISTS idx_obs_history') # drop old
            except Exception:
                pass

            # STORE_FACETS
            migrate_table('store_facets', """CREATE TABLE _store_facets_new (
                provider TEXT NOT NULL DEFAULT 'rappi', store_id TEXT NOT NULL, facet_type TEXT NOT NULL, raw_value TEXT NOT NULL,
                source TEXT, last_seen DATETIME, UNIQUE(provider, store_id, facet_type, raw_value))""")

            # PRODUCT_MEMBERSHIPS
            migrate_table('product_memberships', """CREATE TABLE _product_memberships_new (
                provider TEXT NOT NULL DEFAULT 'rappi', store_id TEXT NOT NULL, product_id TEXT NOT NULL, raw_type TEXT, raw_name TEXT NOT NULL, raw_id TEXT,
                path TEXT, source TEXT, last_seen DATETIME, semantic_type TEXT DEFAULT 'UNKNOWN', semantic_reason TEXT DEFAULT 'not_classified',
                UNIQUE(provider, store_id, product_id, raw_type, raw_name, path))""")

            # ALERTS
            migrate_table('alerts', """CREATE TABLE _alerts_new (
                         id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL DEFAULT 'rappi', product_id TEXT, store_id TEXT,
                         alert_type TEXT, triggered_at DATETIME, price REAL, previous_price REAL, deal_status TEXT, reason TEXT, seen INTEGER DEFAULT 0,
                         UNIQUE(provider, product_id, store_id, alert_type, price))""")
            
            # ALERT_EVENTS
            migrate_table('alert_events', """CREATE TABLE _alert_events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_key TEXT UNIQUE NOT NULL, provider TEXT NOT NULL DEFAULT 'rappi',
                event_type TEXT NOT NULL, store_id TEXT NOT NULL, product_id TEXT NOT NULL, previous_observation_id INTEGER,
                current_observation_id INTEGER, channel TEXT NOT NULL, before_value TEXT, after_value TEXT, metadata TEXT,
                created_at DATETIME NOT NULL, delivery_status TEXT DEFAULT 'pending')""")

        c.execute('UPDATE schema_version SET version = ?', (CURRENT_SCHEMA_VERSION,))
        conn.commit()

def backup_db(db_path, tag="backup"):
    if os.path.exists(db_path):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.{ts}.{tag}.bak"
        
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(backup_path)
        with source:
            source.backup(dest)
        dest.close()
        source.close()
        
        return backup_path
    return None

def db_status(db_path):
    if not os.path.exists(db_path):
        return {"error": "DB not found"}
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    def count(table):
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            return c.fetchone()[0]
        except sqlite3.OperationalError:
            return 0
            
    try:
        c.execute("SELECT version FROM schema_version")
        row = c.fetchone()
        version = row[0] if row else 0
    except sqlite3.OperationalError:
        version = 0
        
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    
    try:
        c.execute("SELECT MAX(started_at) FROM runs")
        last_run = c.fetchone()[0]
    except sqlite3.OperationalError:
        last_run = None
    
    return {
        "path": db_path,
        "size_mb": round(size_mb, 2),
        "version": version,
        "runs": count("runs"),
        "stores": count("stores"),
        "products": count("products"),
        "observations": count("observations"),
        "watchlist": count("watchlist"),
        "last_run": last_run
    }

def db_integrity(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("PRAGMA integrity_check;")
    result = c.fetchone()[0]
    return result

def db_vacuum(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("VACUUM;")
    conn.commit()
    return True
