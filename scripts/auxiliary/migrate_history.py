import sqlite3
import shutil
import os

DB_PATH = os.path.expanduser("~/rappi-deal-hunter/rappi-deals.db")
BACKUP_PATH = os.path.expanduser("~/rappi-deal-hunter/rappi-deals-pre-history.db")

def migrate():
    # 1. Create Backup
    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print("Respaldo creado:", BACKUP_PATH)
    else:
        print("Respaldo ya existía.")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 2. Create 'runs' table
    c.execute('''CREATE TABLE IF NOT EXISTS runs (
                 run_id TEXT PRIMARY KEY, 
                 started_at DATETIME, 
                 finished_at DATETIME, 
                 lat REAL, 
                 lng REAL, 
                 radius REAL, 
                 vertical TEXT, 
                 status TEXT)''')
                 
    # 3. Check if we already migrated observations
    c.execute("PRAGMA table_info(observations)")
    columns = [col[1] for col in c.fetchall()]
    if "run_id" not in columns:
        print("Migrando observations para incluir run_id y UNIQUE constraint...")
        # Rename old
        c.execute("ALTER TABLE observations RENAME TO obs_old")
        
        # Create new
        c.execute('''CREATE TABLE observations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, store_id TEXT, product_id TEXT, 
                  price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, 
                  discount_price REAL, discount_promotion REAL, discount_effective REAL,
                  discount_source TEXT, promotion_type TEXT, promotion_label TEXT,
                  query_term TEXT,
                  UNIQUE(run_id, store_id, product_id))''')
                  
        # Insert legacy run
        c.execute('''INSERT OR IGNORE INTO runs (run_id, started_at, status) 
                     VALUES ('run_legacy_v1', CURRENT_TIMESTAMP, 'MIGRATED')''')
                     
        # Transfer data
        c.execute('''INSERT INTO observations 
                     (run_id, store_id, product_id, price, original_price, stock, timestamp, 
                      discount_price, discount_promotion, discount_effective, discount_source, 
                      promotion_type, promotion_label, query_term)
                     SELECT 'run_legacy_v1', store_id, product_id, price, original_price, stock, timestamp, 
                            discount_price, discount_promotion, discount_effective, discount_source, 
                            promotion_type, promotion_label, query_term 
                     FROM obs_old''')
                     
        c.execute("DROP TABLE obs_old")
        print("Migración completada exitosamente.")
    else:
        print("La base de datos ya cuenta con el esquema histórico.")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
