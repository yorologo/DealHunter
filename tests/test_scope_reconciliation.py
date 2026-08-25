import pytest
import asyncio
from unittest.mock import patch
from dealhunter.crawler_zone import _run_zone_inventory_async
from dealhunter.catalog_sync import CoverageReport
from tests.helpers.db import create_current_schema_db, insert_store, insert_run

@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "scope_reconciliation.db")
    return create_current_schema_db(db_path)

def test_scope_safe_reconciliation(test_db):
    c = test_db.cursor()
    insert_run(test_db, 'run1', started_at='2024-01-01T12:00:00Z', status='RUNNING')
    
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
        insert_store(test_db, store_id=s[0], name=s[1], type=s[2], status='ACTIVE')
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
    insert_run(test_db, 'run2', started_at='2024-01-01T12:00:00Z', status='RUNNING')
    insert_store(test_db, '9', name='Super', type='market', status='ACTIVE')
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
    insert_run(test_db, 'run3', started_at='2024-01-01T12:00:00Z', status='RUNNING')
    insert_store(test_db, '10', name='Super', type='market', status='ACTIVE')
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
