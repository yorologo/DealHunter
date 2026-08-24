import pytest
import sqlite3
import asyncio
from unittest.mock import patch
from dealhunter.crawler_zone import _run_zone_inventory_async
from dealhunter.catalog_sync import CoverageReport

@pytest.fixture
def test_db():
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('''CREATE TABLE runs (run_id TEXT PRIMARY KEY, status TEXT, crawler_mode TEXT, coverage_complete INTEGER, finished_at TIMESTAMP, run_metadata TEXT)''')
    c.execute('''CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT, status TEXT, last_seen_at TIMESTAMP, vertical TEXT)''')
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT)''')
    c.execute('''CREATE TABLE observations (product_id TEXT, availability TEXT)''')
    conn.commit()
    return conn

def test_scope_safe_reconciliation(test_db):
    c = test_db.cursor()
    test_db.execute("INSERT INTO runs (run_id, status) VALUES ('run1', 'RUNNING')")
    
    stores = [
        ('1', 'Rest', 'restaurants'),
        ('2', 'Liq', 'liquor_store'),
        ('3', 'Mall', 'rappimall_parent'),
        ('4', 'Unsupp', 'unknown_type'),
        ('5', 'Super', 'market'),
        ('6', 'TurboOld', 'chiper_extended'),
        ('7', 'Farm', 'Farmatodo')
    ]
    for s in stores:
        c.execute("INSERT INTO stores (store_id, name, type, status) VALUES (?, ?, ?, 'ACTIVE')", s)
    test_db.commit()
    
    mock_merchants = [
        {"store_id": "8", "name": "TurboNew", "type": "chiper_home", "vertical_sub_group": "Turbo"}
    ]
    
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=mock_merchants):
            config = {"max_runtime": 3600, "discovery_mode": "full"}
            state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, test_db, "run1"))
            
            assert state == "COMPLETED"
            
            def get_status(sid):
                c.execute("SELECT status FROM stores WHERE store_id = ?", (sid,))
                return c.fetchone()[0]
                
            assert get_status('1') == 'ACTIVE' 
            assert get_status('2') == 'ACTIVE' 
            assert get_status('3') == 'ACTIVE' 
            assert get_status('4') == 'ACTIVE' 
            
            assert get_status('5') == 'STALE'  
            assert get_status('6') == 'STALE'  
            assert get_status('7') == 'STALE'  
            assert get_status('8') == 'ACTIVE' 

def test_a5_partial_no_stale(test_db):
    c = test_db.cursor()
    test_db.execute("INSERT INTO runs (run_id, status) VALUES ('run2', 'RUNNING')")
    c.execute("INSERT INTO stores (store_id, name, type, status) VALUES ('9', 'Super', 'market', 'ACTIVE')")
    test_db.commit()
    
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "999"}]):
            config = {"max_runtime": -1} # Force PARTIAL immediately due to time
            state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, test_db, "run2"))
            assert state == "PARTIAL"
            c.execute("SELECT status FROM stores WHERE store_id = '9'")
            assert c.fetchone()[0] == 'ACTIVE'

def test_a5_error_no_stale(test_db):
    c = test_db.cursor()
    test_db.execute("INSERT INTO runs (run_id, status) VALUES ('run3', 'RUNNING')")
    c.execute("INSERT INTO stores (store_id, name, type, status) VALUES ('10', 'Super', 'market', 'ACTIVE')")
    test_db.commit()
    
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", side_effect=Exception("Timeout")):
            config = {"max_runtime": 3600}
            try:
                asyncio.run(_run_zone_inventory_async(config, 0, 0, test_db, "run3"))
            except Exception:
                pass
            c.execute("SELECT status FROM stores WHERE store_id = '10'")
            assert c.fetchone()[0] == 'ACTIVE'
