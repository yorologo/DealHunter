import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from dealhunter.db import CURRENT_SCHEMA_VERSION, setup_db


def test_v1_to_current_migration():
    test_db = os.path.join(tempfile.gettempdir(), "test_migration_v1.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT)"
    )
    c.execute(
        """CREATE TABLE products (
           product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
           PRIMARY KEY (store_id, product_id))"""
    )
    c.execute(
        """CREATE TABLE runs (
           run_id TEXT PRIMARY KEY, started_at DATETIME, finished_at DATETIME,
           lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT)"""
    )
    c.execute(
        """CREATE TABLE observations (
           id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, store_id TEXT,
           product_id TEXT, price REAL, original_price REAL, stock INTEGER,
           timestamp DATETIME, discount_price REAL, discount_promotion REAL,
           discount_effective REAL, discount_source TEXT, promotion_type TEXT,
           promotion_label TEXT, query_term TEXT,
           UNIQUE(run_id, store_id, product_id))"""
    )
    c.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO schema_version (version) VALUES (1)")
    c.execute("INSERT INTO stores VALUES ('s1', 'Store 1', 'Brand 1', 'market')")
    c.execute("INSERT INTO products VALUES ('p1', 's1', 'Prod 1', 'Brand 1', 'img')")
    c.execute(
        "INSERT INTO observations (run_id, store_id, product_id, stock) "
        "VALUES ('r1', 's1', 'p1', 10)"
    )
    conn.commit()
    conn.close()

    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == CURRENT_SCHEMA_VERSION
    c.execute("SELECT availability FROM observations WHERE product_id = 'p1'")
    assert c.fetchone()[0] is None
    c.execute("SELECT pack_count FROM products WHERE product_id = 'p1'")
    assert c.fetchone()[0] is None
    conn.close()

    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == CURRENT_SCHEMA_VERSION
    conn.close()

    if os.path.exists(test_db):
        os.remove(test_db)


def test_v2_to_current_migration():
    test_db = os.path.join(tempfile.gettempdir(), "test_migration_v2.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT)"
    )
    c.execute(
        """CREATE TABLE products (
           product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
           PRIMARY KEY (store_id, product_id))"""
    )
    c.execute(
        """CREATE TABLE runs (
           run_id TEXT PRIMARY KEY, started_at DATETIME, finished_at DATETIME,
           lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT)"""
    )
    c.execute(
        """CREATE TABLE observations (
           id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, store_id TEXT,
           product_id TEXT, price REAL, original_price REAL, stock INTEGER,
           timestamp DATETIME, discount_price REAL, discount_promotion REAL,
           discount_effective REAL, discount_source TEXT, promotion_type TEXT,
           promotion_label TEXT, query_term TEXT, availability TEXT,
           UNIQUE(run_id, store_id, product_id))"""
    )
    c.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO schema_version (version) VALUES (2)")
    c.execute("INSERT INTO stores VALUES ('s1', 'Store 1', 'Brand 1', 'market')")
    c.execute("INSERT INTO products VALUES ('p1', 's1', 'Prod 1', 'Brand 1', 'img')")
    c.execute(
        "INSERT INTO observations (run_id, store_id, product_id, stock, availability) "
        "VALUES ('r1', 's1', 'p1', 10, 'AVAILABLE')"
    )
    conn.commit()
    conn.close()

    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == CURRENT_SCHEMA_VERSION
    c.execute(
        "SELECT normalized_name, quantity, unit, pack_count "
        "FROM products WHERE product_id = 'p1'"
    )
    assert c.fetchone() == (None, None, None, None)
    conn.close()

    if os.path.exists(test_db):
        os.remove(test_db)


def test_v3_to_v4_migration_adds_pack_count():
    test_db = os.path.join(tempfile.gettempdir(), "test_migration_v3.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE products (
           product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT,
           normalized_name TEXT, quantity REAL, unit TEXT,
           normalized_quantity REAL, normalized_unit TEXT, fingerprint TEXT,
           PRIMARY KEY (store_id, product_id))"""
    )
    c.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO schema_version (version) VALUES (3)")
    c.execute(
        "INSERT INTO products VALUES "
        "('p1', 's1', 'Leche 1 L', 'Marca', '', 'leche', 1, 'L', 1, 'L', "
        "'marca|leche|1|l')"
    )
    conn.commit()
    conn.close()

    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == CURRENT_SCHEMA_VERSION
    c.execute("SELECT name, pack_count FROM products WHERE product_id = 'p1'")
    assert c.fetchone() == ("Leche 1 L", None)
    c.execute("PRAGMA table_info(products)")
    assert [row[1] for row in c.fetchall()].count("pack_count") == 1
    conn.close()

    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("PRAGMA table_info(products)")
    assert [row[1] for row in c.fetchall()].count("pack_count") == 1
    conn.close()

    if os.path.exists(test_db):
        os.remove(test_db)



def test_v4_to_v5_migration_adds_alerts():
    test_db = os.path.join(tempfile.gettempdir(), "test_migration_v4.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO schema_version (version) VALUES (4)")
    conn.commit()
    conn.close()

    conn = setup_db(test_db)
    c = conn.cursor()
    c.execute("SELECT version FROM schema_version")
    assert c.fetchone()[0] == CURRENT_SCHEMA_VERSION
    
    # Check alerts table
    c.execute("PRAGMA table_info(alerts)")
    columns = [row[1] for row in c.fetchall()]
    assert "alert_type" in columns
    assert "seen" in columns
    conn.close()

    if os.path.exists(test_db):
        os.remove(test_db)

if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    passed = 0
    for test in tests:
        test()
        passed += 1
        print(f"  PASS  {test.__name__}")
    print(f"\nMigration tests: {passed} total, {passed} passed, 0 failed.")
