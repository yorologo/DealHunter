import sqlite3
import pytest
from dealhunter.web.queries import get_catalog

def test_determinism_ties(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, category TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, pack_count INTEGER, fingerprint TEXT, has_toppings BOOLEAN)''')
    c.execute('''CREATE TABLE stores (store_id TEXT, name TEXT, type TEXT, brand TEXT)''')
    c.execute('''CREATE TABLE observations (run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, availability TEXT)''')
    
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'MyStore', 'market', 'Brand')")
    c.execute("INSERT INTO products VALUES ('p1', 's1', 'Prod', '', '', 1, '', 1, '', 1, '', 0)")
    
    # Insert two observations with exactly the same timestamp
    c.execute("INSERT INTO observations (run_id, store_id, product_id, timestamp, price, original_price) VALUES ('r1', 's1', 'p1', '2026-08-01T12:00:00', 120.0, 150.0)")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, timestamp, price, original_price) VALUES ('r2', 's1', 'p1', '2026-08-01T12:00:00', 99.0, 150.0)")
    
    conn.commit()

    
    try:
        from dealhunter.db import migrate
        if 'db_path' in locals(): migrate(conn, db_path)
        elif 'test_db' in locals() and isinstance(test_db, str): migrate(conn, test_db)
    except Exception as e:
        print('MIGRATE ERROR:', e)
    
    conn.close()
    
    cat = get_catalog(db_path, {"store": "s1"}, "price_asc", 1)
    
    # By default, SQLite MAX() on tie returns the last inserted row (which is price 99.0)
    # But let's check if it's 99.0
    assert cat["items"][0]["current_price"] == 99.0


def test_determinism_cross_store(tmp_path):
    db_path = str(tmp_path / 'test.db')
    import sqlite3
    from dealhunter.web.queries import get_catalog
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, category TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, pack_count INTEGER, fingerprint TEXT, has_toppings BOOLEAN)''')
    c.execute('''CREATE TABLE stores (store_id TEXT, name TEXT, type TEXT, brand TEXT)''')
    c.execute('''CREATE TABLE observations (run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, availability TEXT)''')
    
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'Store A', 'market', 'A')")
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s2', 'Store B', 'market', 'B')")
    
    # Same product_id '123' in both stores
    c.execute("INSERT INTO products VALUES ('123', 's1', 'Prod A', '', '', 1, '', 1, '', 1, '', 0)")
    c.execute("INSERT INTO products VALUES ('123', 's2', 'Prod B', '', '', 1, '', 1, '', 1, '', 0)")
    
    c.execute("INSERT INTO observations (run_id, store_id, product_id, timestamp, price, original_price) VALUES ('r1', 's1', '123', '2026-08-01T12:00:00', 100.0, 150.0)")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, timestamp, price, original_price) VALUES ('r1', 's2', '123', '2026-08-01T12:00:00', 50.0, 150.0)")
    
    conn.commit()

    
    # Query without store filter, we should get TWO items!
    # Because get_catalog groups by store_id, product_id
    from dealhunter.db import migrate
    migrate(conn, db_path)
    cat = get_catalog(db_path, {}, "price_asc", 1)
    
    assert len(cat["items"]) == 2
    assert cat["items"][0]["current_price"] == 50.0
    assert cat["items"][1]["current_price"] == 100.0

