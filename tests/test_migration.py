import os
import sys
import sqlite3
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.db import setup_db, CURRENT_SCHEMA_VERSION

def test_v1_to_v2_migration():
    import tempfile
    test_db = os.path.join(tempfile.gettempdir(), "test_migration_v1.db")
    if os.path.exists(test_db):
        os.remove(test_db)
        
    # Create v1 schema
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT)''')
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, PRIMARY KEY (store_id, product_id))''')
    c.execute('''CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at DATETIME, finished_at DATETIME, lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT)''')
    c.execute('''CREATE TABLE observations (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, query_term TEXT, UNIQUE(run_id, store_id, product_id))''')
    c.execute('''CREATE TABLE schema_version (version INTEGER PRIMARY KEY)''')
    c.execute('INSERT INTO schema_version (version) VALUES (1)')
    
    # Insert dummy v1 data
    c.execute("INSERT INTO stores VALUES ('s1', 'Store 1', 'Brand 1', 'market')")
    c.execute("INSERT INTO products VALUES ('p1', 's1', 'Prod 1', 'Brand 1', 'img')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, stock) VALUES ('r1', 's1', 'p1', 10)")
    conn.commit()
    conn.close()
    
    # Run setup_db which should migrate
    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == CURRENT_SCHEMA_VERSION
    
    # Check that availability was added
    c.execute("SELECT availability FROM observations WHERE product_id='p1'")
    row = c.fetchone()
    assert row[0] is None # Old rows have NULL availability
    
    # Idempotency check
    conn.close()
    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == CURRENT_SCHEMA_VERSION
    
    if os.path.exists(test_db):
        os.remove(test_db)

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nMigration tests: {passed} total, {passed} passed, 0 failed.")
