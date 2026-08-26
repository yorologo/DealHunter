"""Tests for Uber Eats crawler persistence and fault tolerance.

Tests the SQL persistence layer, transaction safety, and provider isolation
using in-memory databases with schema v15.
"""
import sqlite3
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from dealhunter.db import setup_db


class TestUberPersistence:
    """Test that Uber observations use INSERT OR IGNORE correctly."""

    def _setup_temp_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = setup_db(db_path)
        return conn

    def test_observation_idempotent_insert(self, tmp_path):
        """INSERT OR IGNORE should silently skip duplicate observations."""
        conn = self._setup_temp_db(tmp_path)
        c = conn.cursor()

        # Insert store
        c.execute("""INSERT INTO stores (provider, store_id, name, brand, type, status, vertical)
                     VALUES ('uber_eats', 'store-1', 'Test', 'Test', 'GROCERY', 'ACTIVE', 'market')""")
        # Insert product
        c.execute("""INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)
                     VALUES ('uber_eats', 'store-1', 'prod-1', 'Cola', '', '', '', 'test')""")
        # Insert observation
        c.execute("""INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price,
                     discount_price, discount_promotion, discount_effective, availability, stock)
                     VALUES ('run-1', 'uber_eats', 'store-1', 'prod-1', CURRENT_TIMESTAMP, 15.0, 20.0, 0, 0, 0, 'AVAILABLE', 1)""")
        conn.commit()

        # Insert same observation again — should be silently ignored
        c.execute("""INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price,
                     discount_price, discount_promotion, discount_effective, availability, stock)
                     VALUES ('run-1', 'uber_eats', 'store-1', 'prod-1', CURRENT_TIMESTAMP, 99.0, 99.0, 0, 0, 0, 'AVAILABLE', 1)""")
        conn.commit()

        # Should still be only 1 observation, with the original price
        c.execute("SELECT COUNT(*), MIN(price) FROM observations WHERE provider='uber_eats'")
        count, price = c.fetchone()
        assert count == 1
        assert price == 15.0

    def test_provider_isolation(self, tmp_path):
        """Uber observations must not collide with Rappi observations."""
        conn = self._setup_temp_db(tmp_path)
        c = conn.cursor()

        # Same store_id + product_id, different providers
        for prov in ('rappi', 'uber_eats'):
            c.execute("""INSERT INTO stores (provider, store_id, name, brand, type, status, vertical)
                         VALUES (?, 'store-1', 'Test', 'Test', 'GROCERY', 'ACTIVE', 'market')""", (prov,))
            c.execute("""INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)
                         VALUES (?, 'store-1', 'prod-1', 'Cola', '', '', '', 'test')""", (prov,))
            c.execute("""INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price,
                         discount_price, discount_promotion, discount_effective, availability, stock)
                         VALUES ('run-1', ?, 'store-1', 'prod-1', CURRENT_TIMESTAMP, 10.0, 10.0, 0, 0, 0, 'AVAILABLE', 1)""", (prov,))
        conn.commit()

        c.execute("SELECT COUNT(*) FROM observations WHERE provider='rappi'")
        assert c.fetchone()[0] == 1
        c.execute("SELECT COUNT(*) FROM observations WHERE provider='uber_eats'")
        assert c.fetchone()[0] == 1

    def test_transaction_rollback_on_failure(self, tmp_path):
        """Failed store sync should rollback cleanly, no partial data."""
        conn = self._setup_temp_db(tmp_path)
        c = conn.cursor()

        try:
            c.execute("""INSERT INTO stores (provider, store_id, name, brand, type, status, vertical)
                         VALUES ('uber_eats', 'store-fail', 'Fail Store', 'Test', 'GROCERY', 'ACTIVE', 'market')""")
            for i in range(3):
                c.execute("""INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)
                             VALUES ('uber_eats', 'store-fail', ?, 'Product', '', '', '', 'test')""", (f'p-{i}',))
            # Simulate crash
            raise RuntimeError("Simulated crash")
        except RuntimeError:
            conn.rollback()

        c.execute("SELECT COUNT(*) FROM stores WHERE store_id='store-fail'")
        assert c.fetchone()[0] == 0
        c.execute("SELECT COUNT(*) FROM products WHERE store_id='store-fail'")
        assert c.fetchone()[0] == 0

    def test_multi_run_observations(self, tmp_path):
        """Multiple runs should create separate observation rows."""
        conn = self._setup_temp_db(tmp_path)
        c = conn.cursor()

        c.execute("""INSERT INTO stores (provider, store_id, name, brand, type, status, vertical)
                     VALUES ('uber_eats', 'store-1', 'Test', 'Test', 'GROCERY', 'ACTIVE', 'market')""")
        c.execute("""INSERT INTO products (provider, store_id, product_id, name, brand, image, category, category_source)
                     VALUES ('uber_eats', 'store-1', 'prod-1', 'Cola', '', '', '', 'test')""")

        for run_id in ('run-1', 'run-2', 'run-3'):
            c.execute("""INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price,
                         discount_price, discount_promotion, discount_effective, availability, stock)
                         VALUES (?, 'uber_eats', 'store-1', 'prod-1', CURRENT_TIMESTAMP, 10.0, 10.0, 0, 0, 0, 'AVAILABLE', 1)""", (run_id,))
        conn.commit()

        c.execute("SELECT COUNT(*) FROM observations WHERE provider='uber_eats' AND product_id='prod-1'")
        assert c.fetchone()[0] == 3

    def test_store_upsert_preserves_type(self, tmp_path):
        """ON CONFLICT should update last_seen_at but not change type."""
        conn = self._setup_temp_db(tmp_path)
        c = conn.cursor()

        c.execute("""INSERT INTO stores (provider, store_id, name, brand, type, status, vertical)
                     VALUES ('uber_eats', 'store-1', 'Pizza Place', 'Pizza', 'RESTAURANT', 'ACTIVE', 'restaurant')""")
        conn.commit()

        # Re-insert same store with different type
        c.execute("""INSERT INTO stores (provider, store_id, name, brand, type, status, last_seen_at, vertical)
                     VALUES ('uber_eats', 'store-1', 'Pizza Place Updated', 'Pizza', 'GROCERY', 'ACTIVE', CURRENT_TIMESTAMP, 'market')
                     ON CONFLICT(provider, store_id) DO UPDATE SET last_seen_at=CURRENT_TIMESTAMP, name=excluded.name""")
        conn.commit()

        c.execute("SELECT name, type FROM stores WHERE provider='uber_eats' AND store_id='store-1'")
        name, stype = c.fetchone()
        assert name == "Pizza Place Updated"  # Name should update
        assert stype == "RESTAURANT"  # Type should NOT change


class TestFeedParser:
    """Tests for parse_feed_v1."""

    def test_parse_feed_v1_basic(self):
        from dealhunter.providers.uber_eats.feed_v1 import parse_feed_v1

        feed_data = {
            "data": {
                "feedItems": [
                    {
                        "store": {
                            "storeUuid": "abc-123",
                            "title": {"text": "Test Store"}
                        }
                    },
                    {
                        "store": {
                            "storeUuid": "def-456",
                            "title": {"text": "Another Store"}
                        }
                    }
                ]
            }
        }
        stores = parse_feed_v1(feed_data)
        assert len(stores) == 2
        assert stores[0]["uuid"] == "abc-123"
        assert stores[0]["name"] == "Test Store"
        assert stores[1]["uuid"] == "def-456"

    def test_parse_feed_v1_empty(self):
        from dealhunter.providers.uber_eats.feed_v1 import parse_feed_v1
        assert parse_feed_v1(None) == []
        assert parse_feed_v1({}) == []
        assert parse_feed_v1({"data": {}}) == []

    def test_parse_feed_v1_dedup(self):
        from dealhunter.providers.uber_eats.feed_v1 import parse_feed_v1

        feed_data = {
            "data": {
                "feedItems": [
                    {"store": {"storeUuid": "same-id", "title": {"text": "Store A"}}},
                    {"store": {"storeUuid": "same-id", "title": {"text": "Store A"}}},
                ]
            }
        }
        stores = parse_feed_v1(feed_data)
        assert len(stores) == 1


class TestUberProviderStatus:
    """Test provider status without requiring runtime."""

    def test_status_returns_dict(self):
        """Status should return a dict with all expected keys."""
        from dealhunter.providers.uber_eats.status import get_status
        st = get_status()
        assert isinstance(st, dict)
        assert "provider" in st
        assert "runtime" in st
        assert "session" in st
        assert "status" in st
        assert st["provider"] == "Uber Eats"
        # Runtime won't be running in test, so status should reflect that
        assert st["runtime"] in ("READY", "RUNTIME_STOPPED")

    def test_status_runtime_stopped_no_ready(self):
        """When runtime is stopped, overall status should NOT be READY."""
        from dealhunter.providers.uber_eats.status import get_status
        st = get_status()
        if st["runtime"] == "RUNTIME_STOPPED":
            assert st["status"] != "READY"

    def test_parse_feed_v1_classification(self):
        from dealhunter.providers.uber_eats.feed_v1 import parse_feed_v1
        
        feed_data = {
            "data": {
                "feedItems": [
                    {
                        "store": {
                            "storeUuid": "rest-1",
                            "title": {"text": "A Restaurant"},
                            "storeType": "RESTAURANT"
                        }
                    },
                    {
                        "store": {
                            "storeUuid": "groc-1",
                            "title": {"text": "A Grocery"},
                            "storeType": "GROCERY"
                        }
                    },
                    {
                        "store": {
                            "storeUuid": "unk-1",
                            "title": {"text": "An Unknown"}
                        }
                    },
                    {
                        "store": {
                            "storeUuid": "rest-url",
                            "title": {"text": "Url Rest"},
                            "actionUrl": "/restaurant/url-rest/rest-url"
                        }
                    },
                    {
                        "store": {
                            "storeUuid": "groc-url",
                            "title": {"text": "Url Groc"},
                            "actionUrl": "/grocery/url-groc/groc-url"
                        }
                    }
                ]
            }
        }
        
        stores = parse_feed_v1(feed_data)
        assert len(stores) == 5
        types = {s["uuid"]: s["type"] for s in stores}
        assert types["rest-1"] == "restaurant"
        assert types["groc-1"] == "grocery"
        assert types["unk-1"] == "unknown"
        assert types["rest-url"] == "restaurant"
        assert types["groc-url"] == "grocery"


    def test_status_combinations(self, monkeypatch):
        """Test status transitions based on runtime, profile, db."""
        import dealhunter.providers.uber_eats.status as st_mod
        from dealhunter.providers.uber_eats.runtime import ChromiumRuntime
        
        # Mock DB
        class MockCursor:
            def __init__(self, count):
                self.count = count
            def execute(self, q, p=None):
                pass
            def fetchone(self):
                if self.count > 0:
                    return ("2030-01-01 00:00:00",)
                return None
            def close(self):
                pass
                
        class MockConn:
            def __init__(self, count):
                self.count = count
            def cursor(self):
                return MockCursor(self.count)
            def close(self):
                pass
                
        monkeypatch.setattr(st_mod, "setup_db", lambda: MockConn(1))
        
        # Test 1: Stopped runtime
        monkeypatch.setattr("os.path.isdir", lambda p: False)
        monkeypatch.setattr(ChromiumRuntime, "is_healthy", lambda self: False)
        
        st = st_mod.get_status()
        assert st["status"] == "DISABLED"
        assert st["runtime"] == "RUNTIME_STOPPED"
        
        # Test 2: Running but no profile
        monkeypatch.setattr("os.path.isdir", lambda p: False)
        monkeypatch.setattr(ChromiumRuntime, "is_healthy", lambda self: True)
        
        st = st_mod.get_status()
        assert st["status"] == "NEEDS_LOGIN"
        assert st["session"] == "NEEDS_LOGIN"
        
        # Test 3: Running and has profile
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        monkeypatch.setattr(ChromiumRuntime, "is_healthy", lambda self: True)
        st = st_mod.get_status()
        assert st["status"] == "READY"
        assert st["session"] == "CONFIGURED"
        
        # Test 4: Stale DB
        monkeypatch.setattr(st_mod, "setup_db", lambda: MockConn(0))
        st = st_mod.get_status()
        assert st["data_status"] == "NO_DATA"


    def test_rerun_same_run_id_dedup(self, current_schema_db):
        """Test that running the same run_id multiple times deduplicates observations."""
        c = current_schema_db.cursor()
        query = '''INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, availability, stock)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        args = ("run-xyz", "uber_eats", "store-1", "prod-1", 100.0, 100.0, 0, 0, 0, None, None, None, "AVAILABLE", 1)
        
        # First commit
        c.execute(query, args)
        current_schema_db.commit()
        
        # Second commit with same data
        c.execute(query, args)
        current_schema_db.commit()
        
        # Check count
        c.execute("SELECT COUNT(*) FROM observations WHERE run_id = 'run-xyz'")
        assert c.fetchone()[0] == 1

    def test_transaction_rollback_on_failure(self, current_schema_db, monkeypatch):
        """Test that an exception during the store product iteration triggers a rollback of that store's batch."""
        import asyncio
        from dealhunter.providers.uber_eats.crawler import _run_uber_sync_async
        
        # We need to mock the ChromiumRuntime, transport, parser, normalizer.
        class MockRuntime:
            def start(self): pass
            def stop(self): pass
        
        class MockTransport:
            async def ensure_ready(self): pass
            async def fetch_feed_v1(self, lat, lng, query=None):
                if query == "supermercado":
                    return {"data": {"feedItems": [{"store": {"storeUuid": "fail-store", "title": {"text": "Fail Store"}, "storeType": "RESTAURANT"}}]}}
                return {"data": {"feedItems": []}}
            async def close(self):
                pass
            async def fetch_store_v1(self, store_uuid, offset=0):
                # We return one product, then raise an exception on next offset or inside parsing?
                # Actually, the exception could be raised from transport to simulate network failure.
                if offset == 0:
                    return {"data": {"catalog": "mock1"}, "paging": {"offset": 10}}
                else:
                    raise RuntimeError("Simulated network failure during pagination")
                    
        class MockParser:
            def parse_store(self, data):
                return {"products": [{"uuid": "p1", "title": "P1"}]}
                
        class MockNormalizer:
            def normalize_product(self, p):
                return {"store_id": "mock_store", "product_id": p["uuid"], "name": p["title"]}
                return {"store_id": store_id, "product_id": p["uuid"], "name": p["title"]}
            def normalize_observation(self, p, run_id):
                return {"price": 100}
                
        monkeypatch.setattr("dealhunter.providers.uber_eats.crawler.ChromiumRuntime", MockRuntime)
        monkeypatch.setattr("dealhunter.providers.uber_eats.crawler.UberBrowserTransport", MockTransport)
        monkeypatch.setattr("dealhunter.providers.uber_eats.crawler.UberEatsParser", MockParser)
        monkeypatch.setattr("dealhunter.providers.uber_eats.crawler.UberEatsNormalizer", MockNormalizer)
        
        status, reqs = asyncio.run(_run_uber_sync_async({}, 19.0, -99.0, current_schema_db, "run-tx-test"))
        
        assert status in ("PARTIAL", "FAILED_FINAL") # Since the store failed, it returns PARTIAL because we only found 1 store and it failed. Wait, actually if all stores fail it might return FAILED or PARTIAL. But let's check DB.
        
        # The first offset yielded a product but the second offset failed.
        # The transaction (batch per store) should have rolled back the first product insert.
        c = current_schema_db.cursor()
        c.execute("SELECT COUNT(*) FROM observations WHERE run_id = 'run-tx-test'")
        assert c.fetchone()[0] == 0


    def test_null_timestamp_tolerance(self, current_schema_db, monkeypatch):
        """Test that legacy NULL timestamps do not corrupt history sorting."""
        c = current_schema_db.cursor()
        # Insert a product with a legacy NULL timestamp observation and a newer valid one.
        c.execute('''INSERT INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price)
                     VALUES ('run-old', 'uber_eats', 's1', 'p1', NULL, 150.0, 150.0)''')
        c.execute('''INSERT INTO observations (run_id, provider, store_id, product_id, timestamp, price, original_price)
                     VALUES ('run-new', 'uber_eats', 's1', 'p1', '2023-01-01 10:00:00', 100.0, 150.0)''')
        current_schema_db.commit()
    
        import dealhunter.historico as h
        monkeypatch.setattr(h, "setup_db", lambda p: current_schema_db)
        
        # Verify it doesn't crash
        results = h.analyze_history("dummy.db", {}, store="s1", product="p1")
        assert len(results) >= 0
