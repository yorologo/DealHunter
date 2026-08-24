import pytest
from unittest.mock import patch
from dealhunter.crawler_zone import _run_zone_inventory_async
import sqlite3
import asyncio

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('''CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at DATETIME, finished_at DATETIME, 
                 lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT, crawler_mode TEXT, coverage_complete INTEGER DEFAULT 0,
                 run_metadata TEXT, source TEXT)''')
    c.execute("""CREATE TABLE store_facets (store_id TEXT, facet_type TEXT, raw_value TEXT, source TEXT, last_seen DATETIME, UNIQUE(store_id, facet_type, raw_value))""")
    c.execute("""CREATE TABLE product_memberships (store_id TEXT, product_id TEXT, raw_type TEXT, raw_name TEXT, raw_id TEXT, path TEXT, source TEXT, last_seen DATETIME, UNIQUE(store_id, product_id, raw_type, raw_name, path))""")
    c.execute('''CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT, status TEXT, last_seen_at DATETIME, vertical TEXT)''')
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, 
                 normalized_name TEXT, quantity REAL, unit TEXT, normalized_quantity REAL, normalized_unit TEXT, 
                 fingerprint TEXT, pack_count INTEGER, category TEXT, has_toppings INTEGER, category_source TEXT,
                 UNIQUE(product_id, store_id))''')
    c.execute('''CREATE TABLE observations (id INTEGER PRIMARY KEY, run_id TEXT, store_id TEXT, product_id TEXT, 
                 price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, 
                 discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, 
                 promotion_label TEXT, query_term TEXT, availability TEXT, has_pro_offer INTEGER DEFAULT 0, pro_price REAL, pro_discount_effective REAL, limit_info TEXT, UNIQUE(run_id, store_id, product_id))''')
    conn.commit()
    return conn

def test_valid_session_zone_inventory(db_conn):
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=[{"id": "p1", "name": "Prod 1"}]):
                db_conn.cursor().execute('INSERT INTO runs (run_id) VALUES ("run1")'); state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run1"))
                assert state == "COMPLETED"
                c = db_conn.cursor()
                c.execute("SELECT crawler_mode, coverage_complete FROM runs WHERE run_id='run1'")
                res = c.fetchone()
                assert res[0] == "ZONE_INVENTORY"
                assert res[1] == 1
                c.execute("SELECT status FROM stores WHERE store_id='1'")
                assert c.fetchone()[0] == "ACTIVE"

def test_expired_session_fallback(db_conn):
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", side_effect=Exception("HTTP 401 Unauthorized")):
            state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run2"))
            assert state == "SESSION_EXPIRED"

def test_store_reconciliation_missing_product(db_conn):
    c = db_conn.cursor()
    c.execute("INSERT INTO stores (store_id, status) VALUES ('1', 'ACTIVE')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p1', '1', 'Prod 1')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p2', '1', 'Prod 2')")
    db_conn.commit()
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=[{"id": "p1", "name": "Prod 1"}]):
                state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run3"))
                c.execute("SELECT availability FROM observations WHERE product_id='p2' AND run_id='run3'")
                res = c.fetchone()
                assert res is not None
                assert res[0] == "UNAVAILABLE"

def test_missing_store_stale(db_conn):
    c = db_conn.cursor()
    c.execute("INSERT INTO stores (store_id, status, type) VALUES ('2', 'ACTIVE', 'market')")
    db_conn.commit()
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=[]):
                state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run4"))
                c.execute("SELECT status FROM stores WHERE store_id='2'")
                assert c.fetchone()[0] == "STALE"

def test_mid_run_401_preserves_state(db_conn):
    c = db_conn.cursor()
    c.execute("INSERT INTO stores (store_id, status) VALUES ('1', 'ACTIVE')")
    c.execute("INSERT INTO stores (store_id, status, type) VALUES ('2', 'ACTIVE', 'market')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p1', '1', 'Prod 1')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p2', '1', 'Prod 2')")
    db_conn.commit()
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}, {"store_id": "2", "name": "Store B"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", side_effect=Exception("HTTP 401 Unauthorized")):
                state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run5"))
                assert state == "SESSION_EXPIRED"
                c.execute("SELECT COUNT(*) FROM observations WHERE product_id='p2' AND availability='UNAVAILABLE'")
                assert c.fetchone()[0] == 0
                c.execute("SELECT status FROM stores WHERE store_id='2'")
                assert c.fetchone()[0] == "ACTIVE"
