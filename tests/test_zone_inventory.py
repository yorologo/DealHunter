import pytest
from unittest.mock import patch
from dealhunter.crawler_zone import _run_zone_inventory_async
import asyncio
from tests.helpers.db import (
    create_current_schema_db,
    insert_product,
    insert_run,
    insert_store,
    insert_store_facet,
)

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


def test_rappi_reconciliation_does_not_mutate_colliding_uber_rows(db_conn):
    insert_store(db_conn, '1', name='Rappi Shared', status='ACTIVE', provider='rappi')
    insert_store(db_conn, '1', name='Uber Shared', status='ACTIVE', provider='uber_eats')
    insert_store(db_conn, '2', name='Uber Other', status='ACTIVE', type='market', provider='uber_eats')
    insert_product(db_conn, 'p2', '1', name='Rappi Missing', provider='rappi')
    insert_product(db_conn, 'p2', '1', name='Uber Product', provider='uber_eats')
    insert_store_facet(db_conn, '1', 'speed', 'Rappi Old', provider='rappi')
    insert_store_facet(db_conn, '1', 'speed', 'Uber Keep', provider='uber_eats')
    insert_run(db_conn, 'run-provider-scope', started_at='2026-08-01T12:00:00Z')
    db_conn.commit()

    config = {"max_runtime": 3600}
    merchants = [{"store_id": "1", "name": "Rappi Shared", "tags": ["Rappi New"]}]
    items = [{"id": "p1", "name": "Rappi Seen", "is_available": True}]
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True), \
         patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=merchants), \
         patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=items), \
         patch("dealhunter.crawler_zone.time.sleep", return_value=None):
        state, _ = asyncio.run(
            _run_zone_inventory_async(config, 0, 0, db_conn, 'run-provider-scope')
        )

    assert state == 'COMPLETED'
    c = db_conn.cursor()
    rappi_unavailable = c.execute(
        """SELECT COUNT(*) FROM observations
           WHERE run_id = 'run-provider-scope' AND provider = 'rappi'
             AND store_id = '1' AND product_id = 'p2' AND availability = 'UNAVAILABLE'"""
    ).fetchone()[0]
    uber_observations = c.execute(
        "SELECT COUNT(*) FROM observations WHERE run_id = 'run-provider-scope' AND provider = 'uber_eats'"
    ).fetchone()[0]
    uber_facets = c.execute(
        "SELECT raw_value FROM store_facets WHERE provider = 'uber_eats' AND store_id = '1'"
    ).fetchall()
    uber_status = c.execute(
        "SELECT status FROM stores WHERE provider = 'uber_eats' AND store_id = '2'"
    ).fetchone()[0]

    assert rappi_unavailable == 1
    assert uber_observations == 0
    assert uber_facets == [('Uber Keep',)]
    assert uber_status == 'ACTIVE'
