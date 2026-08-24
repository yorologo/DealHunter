import sqlite3
import pytest
from dealhunter.web.queries import get_product_detail, get_catalog

def test_get_product_detail_mapping(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, category TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, pack_count INTEGER, fingerprint TEXT, has_toppings BOOLEAN)''')
    c.execute('''CREATE TABLE stores (store_id TEXT, name TEXT, type TEXT, brand TEXT)''')
    c.execute('''CREATE TABLE alerts (product_id TEXT, store_id TEXT, alert_type TEXT, triggered_at DATETIME)''')
    c.execute('''CREATE TABLE watchlist (query TEXT, enabled INTEGER, target_price REAL)''')
    c.execute('''CREATE TABLE observations (run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, availability TEXT)''')
    
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'MyStore', 'BrandStore', 'market')")
    c.execute("INSERT INTO products VALUES ('p1', 's1', 'Test Product', 'MyBrand', 'MyCat', 500, 'g', 0.5, 'kg', 1, 'fp', 0)")
    c.execute("INSERT INTO observations VALUES ('r1', 's1', 'p1', 100.0, 150.0, 10, '2023-01-01T12:00:00Z', 0, 0, 0, '', '', '', 'AVAILABLE')")
    conn.commit()

    
    try:
        from dealhunter.db import migrate
        if 'db_path' in locals(): migrate(conn, db_path)
        elif 'test_db' in locals() and isinstance(test_db, str): migrate(conn, test_db)
    except Exception as e:
        print('MIGRATE ERROR:', e)
    
    conn.close()
    
    p = get_product_detail(db_path, 's1', 'p1')
    assert p["product_name"] == "Test Product"
    assert p["store_name"] == "MyStore"
    assert p["store_type"] == "market"
    assert p["brand"] == "MyBrand"
    assert p["category"] == "MyCat"
    assert p["quantity"] == 500
    assert p["unit"] == "g"
    assert p["normalized_quantity"] == 0.5
    assert p["normalized_unit"] == "kg"
    assert p["pack_count"] == 1

def test_get_catalog_sorting(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, category TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, pack_count INTEGER, fingerprint TEXT, has_toppings BOOLEAN)''')
    c.execute('''CREATE TABLE stores (store_id TEXT, name TEXT, type TEXT, brand TEXT)''')
    c.execute('''CREATE TABLE observations (run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, availability TEXT)''')
    
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'MyStore', 'BrandStore', 'market')")
    c.execute("INSERT INTO products VALUES ('p1', 's1', 'P1', '', '', 1, '', 1, '', 1, '', 0)")
    c.execute("INSERT INTO observations VALUES ('r1', 's1', 'p1', 90.0, 100.0, 10, '2023-01-01T12:00:00Z', 0, 0, 10.0, '', '', '', 'AVAILABLE')")
    c.execute("INSERT INTO products VALUES ('p2', 's1', 'P2', '', '', 1, '', 1, '', 1, '', 0)")
    c.execute("INSERT INTO observations VALUES ('r1', 's1', 'p2', 50.0, 100.0, 10, '2023-01-01T12:00:00Z', 0, 0, 50.0, '', '', '', 'AVAILABLE')")
    c.execute("INSERT INTO products VALUES ('p3', 's1', 'P3', '', '', 1, '', 1, '', 1, '', 0)")
    c.execute("INSERT INTO observations VALUES ('r1', 's1', 'p3', 800.0, 1000.0, 10, '2023-01-01T12:00:00Z', 0, 0, 20.0, '', '', '', 'AVAILABLE')")
    conn.commit()

    
    try:
        from dealhunter.db import migrate
        if 'db_path' in locals(): migrate(conn, db_path)
        elif 'test_db' in locals() and isinstance(test_db, str): migrate(conn, test_db)
    except Exception as e:
        print('MIGRATE ERROR:', e)
    
    conn.close()
    
    cat_desc = get_catalog(db_path, {"vertical": "market"}, "discount", 1, 10)
    assert cat_desc["items"][0]["product_id"] == "p2"
    assert cat_desc["items"][1]["product_id"] == "p3"
    assert cat_desc["items"][2]["product_id"] == "p1"
    
    cat_sav = get_catalog(db_path, {"vertical": "market"}, "savings", 1, 10)
    assert cat_sav["items"][0]["product_id"] == "p3"
    assert cat_sav["items"][1]["product_id"] == "p2"
    assert cat_sav["items"][2]["product_id"] == "p1"

