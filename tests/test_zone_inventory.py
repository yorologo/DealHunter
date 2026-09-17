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


def test_merchant_failure_forces_partial_and_blocks_stale_reconciliation(db_conn):
    insert_store(db_conn, 'legacy', name='Legacy Store', status='ACTIVE', type='market')
    insert_run(db_conn, 'run-partial-failure', started_at='2026-09-16T12:00:00Z', status='RUNNING')
    db_conn.commit()

    async def failed_catalog(self, store_id, report):
        report.merchants_attempted += 1
        report.merchants_failed += 1
        return []

    config = {"max_runtime": 3600, "discovery_mode": "full"}
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True), \
         patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "seen", "name": "Seen Store", "type": "market"}]), \
         patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", new=failed_catalog), \
         patch("dealhunter.crawler_zone.time.sleep", return_value=None):
        state, _ = asyncio.run(
            _run_zone_inventory_async(config, 0, 0, db_conn, 'run-partial-failure')
        )

    assert state == 'PARTIAL'
    row = db_conn.execute(
        "SELECT status, coverage_complete FROM runs WHERE run_id='run-partial-failure'"
    ).fetchone()
    assert row == ('PARTIAL', 0)
    assert db_conn.execute(
        "SELECT status FROM stores WHERE provider='rappi' AND store_id='legacy'"
    ).fetchone()[0] == 'ACTIVE'


def test_structured_catalog_failure_is_partial(db_conn):
    from dealhunter.catalog_sync import CatalogFetchResult

    insert_run(db_conn, "run-structured-failure", started_at="2026-09-16T12:00:00Z", status="RUNNING")
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True), \
         patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A", "type": "market"}]), \
         patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=CatalogFetchResult([], False, "TIMEOUT")), \
         patch("dealhunter.crawler_zone.time.sleep", return_value=None):
        state, _ = asyncio.run(_run_zone_inventory_async({"max_runtime": 3600}, 0, 0, db_conn, "run-structured-failure"))
    assert state == "PARTIAL"
    assert db_conn.execute("SELECT coverage_complete FROM runs WHERE run_id='run-structured-failure'").fetchone()[0] == 0


def test_structured_401_expires_session_without_reconciliation(db_conn):
    from dealhunter.catalog_sync import CatalogFetchResult

    insert_store(db_conn, "legacy401", status="ACTIVE", type="market")
    insert_run(db_conn, "run-structured-401", started_at="2026-09-16T12:00:00Z", status="RUNNING")
    db_conn.commit()
    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True), \
         patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=[{"store_id": "1", "name": "Store A", "type": "market"}]), \
         patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=CatalogFetchResult([], False, "ACCOUNT_SESSION_UNAVAILABLE")):
        state, _ = asyncio.run(_run_zone_inventory_async({"max_runtime": 3600}, 0, 0, db_conn, "run-structured-401"))
    assert state == "SESSION_EXPIRED"
    assert db_conn.execute("SELECT status FROM stores WHERE store_id='legacy401'").fetchone()[0] == "ACTIVE"


def test_zone_inventory_persists_real_merchant_progress(db_conn):
    import json
    from dealhunter.run_lifecycle import update_run_progress as real_update

    insert_run(
        db_conn,
        "run-progress-zone",
        started_at="2026-09-17T12:00:00Z",
        status="RUNNING",
    )
    db_conn.commit()
    merchants = [
        {"store_id": "1", "name": "Store A", "type": "market"},
        {"store_id": "2", "name": "Store B", "type": "market"},
    ]
    calls = []

    def record_progress(conn, run_id, **kwargs):
        calls.append(dict(kwargs))
        return real_update(conn, run_id, **kwargs)

    with patch("dealhunter.crawler_zone.RappiSessionProvider.is_authenticated", return_value=True), \
         patch("dealhunter.crawler_zone.MerchantDiscovery.discover_merchants", return_value=merchants), \
         patch("dealhunter.crawler_zone.CPGCatalogAdapter.fetch_full_catalog", return_value=[]), \
         patch("dealhunter.crawler_zone.update_run_progress", side_effect=record_progress):
        state, _ = asyncio.run(
            _run_zone_inventory_async(
                {"max_runtime": 3600, "discovery_mode": "full"},
                0,
                0,
                db_conn,
                "run-progress-zone",
                dry_run=True,
            )
        )

    assert state == "COMPLETED"
    phases = [call["phase"] for call in calls]
    assert phases[0] == "DISCOVERING"
    assert "CRAWLING" in phases
    assert phases[-1] == "FINALIZING"
    crawling_completed = [
        call["completed"] for call in calls if call["phase"] == "CRAWLING"
    ]
    assert crawling_completed == [0, 1, 2]

    raw = db_conn.execute(
        "SELECT run_metadata FROM runs WHERE run_id='run-progress-zone'"
    ).fetchone()[0]
    metadata = json.loads(raw)
    assert metadata["progress"]["phase"] == "FINALIZING"
    assert metadata["progress"]["completed"] == 2
    assert metadata["progress"]["total"] == 2
    assert metadata["merchants_discovered"] >= 0
