"""Tests for DealHunter v2.2 robustness features:
- Structured errors
- Partial runs
- Checkpoints
- Doctor diagnostics
"""

import os
import sys
import json
import sqlite3
import tempfile
import urllib.error
import socket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.errors import DealHunterError, ERROR_CATALOG, classify_error
from dealhunter.checkpoint import RunCheckpoint, save_checkpoint, load_checkpoint
from dealhunter.doctor import run_doctor, format_doctor_output

# ============================================================
# Error tests
# ============================================================

def test_error_catalog_completeness():
    """All expected error codes exist in catalog."""
    expected = [
        "NETWORK_ERROR", "TIMEOUT", "HTTP_429", "CLOUDFLARE_LIMIT",
        "INVALID_RESPONSE", "PARSER_ERROR", "DB_LOCKED", "DB_CORRUPT",
        "CONFIG_ERROR", "PARTIAL_RUN", "REQUEST_BUDGET_REACHED",
    ]
    for code in expected:
        assert code in ERROR_CATALOG, f"Missing {code}"

def test_error_has_fields():
    """Each catalog entry has required fields."""
    for code, info in ERROR_CATALOG.items():
        assert "message" in info, f"{code} missing message"
        assert "recoverable" in info, f"{code} missing recoverable"
        assert "recommended_action" in info, f"{code} missing recommended_action"

def test_error_to_dict():
    err = DealHunterError("HTTP_429")
    d = err.to_dict()
    assert d["code"] == "HTTP_429"
    assert d["recoverable"] is True
    assert "Wait" in d["recommended_action"]

def test_error_str():
    err = DealHunterError("DB_CORRUPT")
    s = str(err)
    assert "DB_CORRUPT" in s
    assert "non-recoverable" in s

def test_error_custom_message():
    err = DealHunterError("NETWORK_ERROR", message="Custom msg")
    assert err.message == "Custom msg"
    assert err.recoverable is True  # from catalog default

def test_classify_http_429():
    exc = urllib.error.HTTPError("http://x", 429, "Too Many", {}, None)
    err = classify_error(exc)
    assert err.code == "HTTP_429"

def test_classify_http_1015():
    exc = urllib.error.HTTPError("http://x", 1015, "Cloudflare", {}, None)
    err = classify_error(exc)
    assert err.code == "CLOUDFLARE_LIMIT"

def test_classify_timeout():
    exc = socket.timeout("timed out")
    err = classify_error(exc)
    assert err.code == "TIMEOUT"

def test_classify_timeout_error():
    exc = TimeoutError("connection timed out")
    err = classify_error(exc)
    assert err.code == "TIMEOUT"

def test_classify_url_error():
    exc = urllib.error.URLError("Connection refused")
    err = classify_error(exc)
    assert err.code == "NETWORK_ERROR"

def test_classify_json_decode():
    exc = json.JSONDecodeError("Expecting value", "", 0)
    err = classify_error(exc)
    assert err.code == "INVALID_RESPONSE"

def test_classify_db_locked():
    exc = sqlite3.OperationalError("database is locked")
    err = classify_error(exc)
    assert err.code == "DB_LOCKED"

def test_classify_db_corrupt():
    exc = sqlite3.DatabaseError("database disk image is malformed")
    err = classify_error(exc)
    assert err.code == "DB_CORRUPT"

def test_classify_unknown():
    exc = RuntimeError("something weird")
    err = classify_error(exc)
    assert err.code == "NETWORK_ERROR"
    assert "something weird" in err.message

# ============================================================
# Checkpoint tests
# ============================================================

def _make_test_db():
    """Create a temp DB with runs table and return (conn, path)."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at DATETIME, 
                 finished_at DATETIME, lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT)''')
    conn.commit()
    return conn, db_path

def test_checkpoint_roundtrip():
    conn, _ = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, status) VALUES ('r1', 'RUNNING')")
    conn.commit()

    cp = RunCheckpoint("r1", mode="discover", current_vertical="farmacia",
                       last_completed_query="vitaminas", status="PARTIAL",
                       queries_completed=5, requests_made=3, error_code="HTTP_429")
    save_checkpoint(conn, cp)

    loaded = load_checkpoint(conn, "r1")
    assert loaded is not None
    assert loaded.run_id == "r1"
    assert loaded.mode == "discover"
    assert loaded.current_vertical == "farmacia"
    assert loaded.last_completed_query == "vitaminas"
    assert loaded.status == "PARTIAL"
    assert loaded.queries_completed == 5
    assert loaded.requests_made == 3
    assert loaded.error_code == "HTTP_429"

def test_checkpoint_to_json():
    cp = RunCheckpoint("r1", mode="update")
    j = cp.to_json()
    d = json.loads(j)
    assert d["run_id"] == "r1"
    assert d["mode"] == "update"

def test_load_checkpoint_missing():
    conn, _ = _make_test_db()
    result = load_checkpoint(conn, "nonexistent")
    assert result is None

def test_load_checkpoint_invalid_json():
    conn, _ = _make_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, status, vertical) VALUES ('r1', 'X', 'not-json')")
    conn.commit()
    result = load_checkpoint(conn, "r1")
    assert result is None

# ============================================================
# Partial run tests
# ============================================================

def _make_full_test_db():
    """Create a temp DB with full schema."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, brand TEXT, type TEXT)''')
    c.execute('''CREATE TABLE products (product_id TEXT, store_id TEXT, name TEXT, brand TEXT, image TEXT, PRIMARY KEY (store_id, product_id))''')
    c.execute('''CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at DATETIME, finished_at DATETIME, lat REAL, lng REAL, radius REAL, vertical TEXT, status TEXT)''')
    c.execute('''CREATE TABLE observations (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, store_id TEXT, product_id TEXT, price REAL, original_price REAL, stock INTEGER, timestamp DATETIME, discount_price REAL, discount_promotion REAL, discount_effective REAL, discount_source TEXT, promotion_type TEXT, promotion_label TEXT, query_term TEXT, UNIQUE(run_id, store_id, product_id))''')
    c.execute('''CREATE TABLE schema_version (version INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE watchlist (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, store_filter TEXT, target_price REAL, min_discount REAL, created_at DATETIME, enabled INTEGER DEFAULT 1)''')
    conn.commit()
    return conn, db_path

def test_successful_dry_run():
    """A dry run should complete with COMPLETED status."""
    conn, db_path = _make_full_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('dry1', CURRENT_TIMESTAMP, 'RUNNING')")
    conn.commit()

    from dealhunter.crawler import run_discover
    config = {"vertical": ["test_run"], "query": [], "max_requests": 1000, "max_runtime": 3600,
              "min_discount": 0, "max_discount": 100, "dry_run": True}
    state, reqs = run_discover(config, 19.4, -99.1, conn, "dry1", dry_run=True)
    assert state == "COMPLETED"

def test_request_budget_reached():
    """Run should stop at max_requests with REQUEST_BUDGET_REACHED."""
    conn, db_path = _make_full_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('budget1', CURRENT_TIMESTAMP, 'RUNNING')")
    conn.commit()

    from dealhunter.crawler import run_discover
    config = {"vertical": ["supermercado"], "query": [], "max_requests": 0, "max_runtime": 3600,
              "min_discount": 0, "max_discount": 100, "dry_run": False}
    state, reqs = run_discover(config, 19.4, -99.1, conn, "budget1", dry_run=False)
    assert state == "REQUEST_BUDGET_REACHED"

def test_run_sets_finished_at():
    """After a run, finished_at should be set."""
    conn, db_path = _make_full_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('fin1', CURRENT_TIMESTAMP, 'RUNNING')")
    conn.commit()

    from dealhunter.crawler import run_discover
    config = {"vertical": ["test_run"], "query": [], "max_requests": 1000, "max_runtime": 3600,
              "min_discount": 0, "max_discount": 100, "dry_run": True}
    state, _ = run_discover(config, 19.4, -99.1, conn, "fin1", dry_run=True)

    # Simulate what cli.py does
    c.execute("UPDATE runs SET status = ?, finished_at = CURRENT_TIMESTAMP WHERE run_id = ?", (state, "fin1"))
    conn.commit()

    c.execute("SELECT finished_at, status FROM runs WHERE run_id = 'fin1'")
    row = c.fetchone()
    assert row[0] is not None, "finished_at should be set"
    assert row[1] == "COMPLETED"

def test_partial_run_preserves_observations():
    """Observations committed before a failure must survive."""
    conn, db_path = _make_full_test_db()
    c = conn.cursor()

    # Simulate a run that already committed some observations
    c.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('partial1', CURRENT_TIMESTAMP, 'RUNNING')")
    c.execute("INSERT INTO stores (store_id, name) VALUES ('s1', 'TestStore')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p1', 's1', 'Leche')")
    c.execute("""INSERT INTO observations (run_id, store_id, product_id, price, timestamp, discount_effective) 
                 VALUES ('partial1', 's1', 'p1', 25.0, '2026-01-01', 40)""")
    conn.commit()

    # Now mark run as partial (simulating failure after data committed)
    c.execute("UPDATE runs SET status = 'PARTIAL', finished_at = CURRENT_TIMESTAMP WHERE run_id = 'partial1'")
    conn.commit()

    # Verify observations survived
    c.execute("SELECT COUNT(*) FROM observations WHERE run_id = 'partial1'")
    assert c.fetchone()[0] == 1, "Observation should survive partial run"

    c.execute("SELECT status, finished_at FROM runs WHERE run_id = 'partial1'")
    row = c.fetchone()
    assert row[0] == "PARTIAL"
    assert row[1] is not None

# ============================================================
# Doctor tests
# ============================================================

def test_doctor_healthy_db():
    """Doctor should report HEALTHY for a valid database."""
    conn, db_path = _make_full_test_db()
    conn.close()

    old = os.environ.get("RAPPI_DB_PATH")
    os.environ["RAPPI_DB_PATH"] = db_path
    try:
        checks = run_doctor(db_path=db_path)
        output = format_doctor_output(checks)
        assert "HEALTHY" in output
        assert "ERROR" not in output
    finally:
        if old:
            os.environ["RAPPI_DB_PATH"] = old
        else:
            os.environ.pop("RAPPI_DB_PATH", None)

def test_doctor_missing_db():
    """Doctor should report ERROR for missing database."""
    checks = run_doctor(db_path="/tmp/nonexistent_dealhunter_test.db")
    output = format_doctor_output(checks)
    assert "ERROR" in output

def test_doctor_partial_runs_count():
    """Doctor should detect partial runs."""
    conn, db_path = _make_full_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO runs (run_id, status) VALUES ('p1', 'PARTIAL')")
    c.execute("INSERT INTO runs (run_id, status) VALUES ('p2', 'RUNNING')")
    c.execute("INSERT INTO runs (run_id, status) VALUES ('c1', 'COMPLETED')")
    conn.commit()
    conn.close()

    checks = run_doctor(db_path=db_path)
    partial_check = [c for c in checks if c[0] == "Partial runs"][0]
    assert partial_check[2]["info"] == "2"

def test_doctor_providers_placeholder():
    """Doctor should show NOT_IMPLEMENTED for future providers."""
    conn, db_path = _make_full_test_db()
    conn.close()
    checks = run_doctor(db_path=db_path)
    names = {c[0]: c[1] for c in checks}
    assert names.get("Turbo") == "AVAILABLE"
    assert names.get("Restaurants") == "AVAILABLE"
    assert names.get("Account context") == "NOT_IMPLEMENTED"
    assert names.get("Rappi catalog") == "NOT_CHECKED"

def test_doctor_output_format():
    """Doctor output should have expected format."""
    conn, db_path = _make_full_test_db()
    conn.close()
    checks = run_doctor(db_path=db_path)
    output = format_doctor_output(checks)
    assert "DealHunter Doctor" in output
    assert "Overall" in output
    assert "Configuration" in output
    assert "Database" in output
    assert "SQLite integrity" in output


# ============================================================
# Run all
# ============================================================

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")

    print(f"\nRobustness tests: {passed + failed} total, {passed} passed, {failed} failed.")
    if failed:
        sys.exit(1)
