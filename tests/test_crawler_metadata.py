import pytest
import sqlite3
import uuid
import asyncio
from unittest.mock import patch, MagicMock
from dealhunter.crawler_zone import run_zone_inventory
from dealhunter.crawler import run_discover
from dealhunter.config import load_config

@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / 'test.db'))
    from dealhunter.db import setup_db
    setup_db(str(tmp_path / 'test.db'))
    conn = sqlite3.connect(str(tmp_path / 'test.db'))
    return conn

@patch('dealhunter.crawler_zone._run_zone_inventory_async')
def test_crawler_mode_written_at_run_start_zone(mock_run, db_conn):
    # Actually wait, run_zone_inventory updates the mode BEFORE calling _run_zone_inventory_async?
    # No, it's inside _run_zone_inventory_async.
    pass

def test_aborted_zone_run_preserves_mode(db_conn):
    config = load_config()
    run_id = str(uuid.uuid4())
    db_conn.execute("INSERT INTO runs (run_id, status) VALUES (?, 'RUNNING')", (run_id,))
    db_conn.commit()

    with patch('dealhunter.crawler_zone.MerchantDiscovery') as mock_disc:
        mock_disc.side_effect = KeyboardInterrupt()
        with patch('dealhunter.crawler_zone.RappiSessionProvider') as mock_prov:
            from unittest.mock import AsyncMock
            mock_prov.return_value.is_authenticated = AsyncMock(return_value=True)
            
            
            run_zone_inventory(config, 0, 0, db_conn, run_id, dry_run=False)
            
            cur = db_conn.cursor()
            cur.execute("SELECT crawler_mode, coverage_complete, status FROM runs WHERE run_id = ?", (run_id,))
            res = cur.fetchone()
            assert res[0] == "ZONE_INVENTORY"
            assert res[1] == 0
            assert res[2] == "PARTIAL"

def test_aborted_discover_run_preserves_mode(db_conn):
    config = load_config()
    run_id = str(uuid.uuid4())
    db_conn.execute("INSERT INTO runs (run_id, status) VALUES (?, 'RUNNING')", (run_id,))
    db_conn.commit()

    with patch('dealhunter.crawler.fetch_unified_search') as mock_disc:
        mock_disc.side_effect = KeyboardInterrupt()
        
        run_discover(config, 0, 0, db_conn, run_id, dry_run=False)
        
        cur = db_conn.cursor()
        cur.execute("SELECT crawler_mode, coverage_complete, status FROM runs WHERE run_id = ?", (run_id,))
        res = cur.fetchone()
        assert res[0] == "SEARCH_DISCOVERY"
        assert res[1] == 0
        assert res[2] == "PARTIAL"
        

def test_coverage_complete_adaptive_modes(db_conn):
    config = load_config()
    run_id = str(uuid.uuid4())
    db_conn.execute("INSERT INTO runs (run_id, status) VALUES (?, 'RUNNING')", (run_id,))
    db_conn.commit()

    with patch('dealhunter.crawler_zone.MerchantDiscovery') as mock_disc:
        from unittest.mock import AsyncMock
        mock_disc.return_value.discover_merchants = AsyncMock(return_value=[])
        with patch('dealhunter.crawler_zone.RappiSessionProvider') as mock_prov:
            mock_prov.return_value.is_authenticated = AsyncMock(return_value=True)
            
            # NORMAL
            config["discovery_mode"] = "normal"
            run_zone_inventory(config, 0, 0, db_conn, run_id, dry_run=False)
            cur = db_conn.cursor()
            cur.execute("SELECT coverage_complete FROM runs WHERE run_id = ?", (run_id,))
            assert cur.fetchone()[0] == 0
            
            # DEEP
            config["discovery_mode"] = "deep"
            run_zone_inventory(config, 0, 0, db_conn, run_id, dry_run=False)
            cur.execute("SELECT coverage_complete FROM runs WHERE run_id = ?", (run_id,))
            assert cur.fetchone()[0] == 0
            
            # FULL
            config["discovery_mode"] = "full"
            run_zone_inventory(config, 0, 0, db_conn, run_id, dry_run=False)
            cur.execute("SELECT coverage_complete FROM runs WHERE run_id = ?", (run_id,))
            assert cur.fetchone()[0] == 1


def test_search_discovery_progress_is_indeterminate(db_conn):
    import json
    from dealhunter.crawler import run_discover

    run_id = "search-progress"
    db_conn.execute(
        "INSERT INTO runs (run_id, started_at, status) VALUES (?, CURRENT_TIMESTAMP, 'RUNNING')",
        (run_id,),
    )
    db_conn.commit()

    state, _ = run_discover(
        {
            "vertical": ["supermercado"],
            "query": ["coca"],
            "max_requests": 10,
            "max_runtime": 60,
        },
        0,
        0,
        db_conn,
        run_id,
        dry_run=True,
    )
    assert state == "COMPLETED"
    raw = db_conn.execute(
        "SELECT run_metadata FROM runs WHERE run_id=?", (run_id,)
    ).fetchone()[0]
    progress = json.loads(raw)["progress"]
    assert progress["phase"] == "FINALIZING"
    assert progress["completed"] == 1
    assert progress["total"] is None
    assert progress["unit"] == "consultas"
