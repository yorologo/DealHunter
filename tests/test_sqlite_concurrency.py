import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import dealhunter.db as db_module
from dealhunter.web.app import create_app


def _seed_current_db(db_path):
    conn = db_module.setup_db(str(db_path))
    conn.execute(
        "INSERT INTO stores (provider, store_id, name, type, vertical) "
        "VALUES ('rappi', 'store-1', 'Store 1', 'market', 'market')"
    )
    conn.execute(
        "INSERT INTO products "
        "(provider, store_id, product_id, name, category, normalized_quantity, normalized_unit) "
        "VALUES ('rappi', 'store-1', 'product-1', 'Product 1', 'Test', 1, 'piece')"
    )
    conn.execute(
        "INSERT INTO runs (run_id, started_at, finished_at, status) "
        "VALUES ('run-1', '2026-09-03T10:00:00', '2026-09-03T10:01:00', 'SUCCESS')"
    )
    conn.execute(
        "INSERT INTO observations "
        "(run_id, provider, store_id, product_id, price, original_price, timestamp) "
        "VALUES ('run-1', 'rappi', 'store-1', 'product-1', 10, 12, '2026-09-03T10:00:00')"
    )
    conn.commit()
    conn.close()


def test_setup_db_on_current_schema_executes_no_ddl(tmp_path, monkeypatch):
    """Opening an already-current database must be a read-only schema path."""
    db_path = tmp_path / "current.db"
    conn = db_module.setup_db(str(db_path))
    conn.close()

    statements = []
    real_connect = sqlite3.connect

    def traced_connect(*args, **kwargs):
        traced = real_connect(*args, **kwargs)
        traced.set_trace_callback(statements.append)
        return traced

    monkeypatch.setattr(db_module.sqlite3, "connect", traced_connect)

    conn = db_module.setup_db(str(db_path))
    conn.close()

    ddl = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith(("CREATE ", "DROP ", "ALTER "))
    ]
    assert ddl == []


def test_fresh_database_has_current_schema_and_trusted_view(tmp_path):
    db_path = tmp_path / "fresh.db"
    conn = db_module.setup_db(str(db_path))

    assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == 16
    view = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = 'trusted_observations'"
    ).fetchone()
    assert view is not None
    assert "JOIN runs r ON o.run_id = r.run_id" in view[0]
    conn.close()


def test_old_database_migrates_without_losing_data(tmp_path):
    db_path = tmp_path / "old.db"
    _seed_current_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE schema_version SET version = 15")
    conn.commit()
    conn.close()

    conn = db_module.setup_db(str(db_path))
    assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == 16
    assert conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
    conn.close()


def test_concurrent_fresh_initialization_is_serialized(tmp_path):
    db_path = tmp_path / "concurrent-fresh.db"
    start = threading.Barrier(8)

    def initialize(_):
        start.wait()
        conn = db_module.setup_db(str(db_path))
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        conn.close()
        return version

    with ThreadPoolExecutor(max_workers=8) as pool:
        versions = list(pool.map(initialize, range(8)))

    assert versions == [16] * 8
    conn = sqlite3.connect(db_path)
    assert conn.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type = 'view' AND name = 'trusted_observations'"
    ).fetchone()[0] == 1
    conn.close()


def test_trusted_view_replacement_is_atomic_for_other_connections(tmp_path):
    db_path = tmp_path / "atomic.db"
    _seed_current_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("DROP VIEW trusted_observations")
    conn.execute(
        "CREATE VIEW trusted_observations AS SELECT o.* FROM observations o"
    )
    conn.commit()
    conn.close()

    before_create = threading.Event()
    allow_create = threading.Event()
    errors = []

    def repair_view():
        worker = sqlite3.connect(db_path, timeout=5)

        def pause_between_drop_and_create(statement):
            normalized = " ".join(statement.upper().split())
            if normalized.startswith("CREATE VIEW TRUSTED_OBSERVATIONS"):
                before_create.set()
                if not allow_create.wait(timeout=5):
                    raise AssertionError("timed out waiting to finish view repair")

        worker.set_trace_callback(pause_between_drop_and_create)
        try:
            db_module.migrate(worker, str(db_path))
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)
        finally:
            worker.close()

    thread = threading.Thread(target=repair_view)
    thread.start()
    assert before_create.wait(timeout=5)

    # The old committed view remains queryable while DROP/CREATE is uncommitted.
    reader = sqlite3.connect(db_path, timeout=5)
    assert reader.execute("SELECT COUNT(*) FROM trusted_observations").fetchone()[0] == 1
    reader.close()

    allow_create.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert errors == []

    conn = sqlite3.connect(db_path)
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = 'trusted_observations'"
    ).fetchone()[0]
    assert "JOIN runs r ON o.run_id = r.run_id" in sql
    conn.close()


def test_concurrent_current_schema_reads_do_not_change_data(tmp_path):
    db_path = tmp_path / "concurrent-read.db"
    _seed_current_db(db_path)

    def read_counts(_):
        conn = db_module.setup_db(str(db_path))
        counts = tuple(
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("stores", "products", "observations", "runs", "trusted_observations")
        )
        conn.close()
        return counts

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(read_counts, range(48)))

    assert results == [(1, 1, 1, 1, 1)] * 48


def test_concurrent_critical_web_requests_return_200(tmp_path):
    db_path = tmp_path / "web.db"
    _seed_current_db(db_path)
    app = create_app({"DATABASE": str(db_path), "SECRET_KEY": "test", "TESTING": False})
    paths = ["/", "/deals", "/best"] * 8

    def request_path(path):
        with app.test_client() as client:
            return client.get(path).status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(request_path, paths))

    assert statuses == [200] * len(paths)


def test_web_reads_survive_controlled_writer_without_schema_changes(tmp_path):
    db_path = tmp_path / "writer.db"
    _seed_current_db(db_path)
    app = create_app({"DATABASE": str(db_path), "SECRET_KEY": "test", "TESTING": False})

    writer = sqlite3.connect(db_path, timeout=5)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute(
        "UPDATE stores SET name = 'Uncommitted Name' "
        "WHERE provider = 'rappi' AND store_id = 'store-1'"
    )

    def request_path(path):
        with app.test_client() as client:
            return client.get(path).status_code

    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            statuses = list(pool.map(request_path, ["/", "/deals", "/best"] * 2))
        assert statuses == [200] * 6
    finally:
        writer.rollback()
        writer.close()

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == 16
    assert conn.execute("SELECT COUNT(*) FROM trusted_observations").fetchone()[0] == 1
    assert conn.execute(
        "SELECT name FROM stores WHERE provider = 'rappi' AND store_id = 'store-1'"
    ).fetchone()[0] == "Store 1"
    conn.close()
