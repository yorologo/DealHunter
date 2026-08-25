import pytest
from unittest.mock import patch
from dealhunter.crawler_zone import _run_zone_inventory_async
import asyncio
from tests.helpers.db import create_current_schema_db, insert_store, insert_product, insert_run

@pytest.fixture
def db_conn(tmp_path):
    db_path = str(tmp_path / "zone_inventory.db")
    return create_current_schema_db(db_path)

def test_valid_session_zone_inventory(db_conn):
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=[{"id": "p1", "name": "Prod 1"}]):
                insert_run(db_conn, "run1", started_at="2024-01-01T12:00:00Z")
                state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run1"))
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
            insert_run(db_conn, "run2", started_at="2024-01-01T12:00:00Z")
            state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run2"))
            assert state == "SESSION_EXPIRED"

def test_store_reconciliation_missing_product(db_conn):
    insert_store(db_conn, '1', status='ACTIVE')
    insert_product(db_conn, 'p1', '1', name='Prod 1')
    insert_product(db_conn, 'p2', '1', name='Prod 2')
    db_conn.commit()
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=[{"id": "p1", "name": "Prod 1"}]):
                insert_run(db_conn, "run3", started_at="2024-01-01T12:00:00Z")
                state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run3"))
                c = db_conn.cursor()
                c.execute("SELECT availability FROM observations WHERE product_id='p2' AND run_id='run3'")
                res = c.fetchone()
                assert res is not None
                assert res[0] == "UNAVAILABLE"

def test_missing_store_stale(db_conn):
    insert_store(db_conn, '2', status='ACTIVE', type='market')
    db_conn.commit()
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=[]):
                insert_run(db_conn, "run4", started_at="2024-01-01T12:00:00Z")
                state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run4"))
                c = db_conn.cursor()
                c.execute("SELECT status FROM stores WHERE store_id='2'")
                assert c.fetchone()[0] == "STALE"

def test_mid_run_401_preserves_state(db_conn):
    insert_store(db_conn, '1', status='ACTIVE')
    insert_store(db_conn, '2', status='ACTIVE', type='market')
    insert_product(db_conn, 'p1', '1', name='Prod 1')
    insert_product(db_conn, 'p2', '1', name='Prod 2')
    db_conn.commit()
    config = {"max_runtime": 3600}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True):
        with patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A"}, {"store_id": "2", "name": "Store B"}]):
            with patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", side_effect=Exception("HTTP 401 Unauthorized")):
                insert_run(db_conn, "run5", started_at="2024-01-01T12:00:00Z")
                state, reqs = asyncio.run(_run_zone_inventory_async(config, 0, 0, db_conn, "run5"))
                assert state == "SESSION_EXPIRED"
                c = db_conn.cursor()
                c.execute("SELECT COUNT(*) FROM observations WHERE product_id='p2' AND availability='UNAVAILABLE'")
                assert c.fetchone()[0] == 0
                c.execute("SELECT status FROM stores WHERE store_id='2'")
                assert c.fetchone()[0] == "ACTIVE"
