import sqlite3

import pytest

from dealhunter.db import setup_db
from dealhunter.run_lifecycle import ActiveRunError, reserve_run


def test_atomic_run_reservation_blocks_second_recent_run(tmp_path):
    db_path = str(tmp_path / "runs.db")
    conn1 = setup_db(db_path)
    conn2 = sqlite3.connect(db_path, timeout=30)
    try:
        assert reserve_run(conn1, "run-a", lat=1.0, lng=2.0, radius=5.0) is True
        with pytest.raises(ActiveRunError, match="active"):
            reserve_run(conn2, "run-b", lat=1.0, lng=2.0, radius=5.0)
    finally:
        conn1.close()
        conn2.close()


def test_reserved_web_run_can_be_adopted_only_by_same_run_id(tmp_path):
    db_path = str(tmp_path / "runs.db")
    conn = setup_db(db_path)
    try:
        assert reserve_run(
            conn, "web-run", lat=1.0, lng=2.0, radius=5.0, source="WEB"
        ) is True
        assert reserve_run(
            conn, "web-run", lat=1.0, lng=2.0, radius=5.0,
            source="CLI", allow_existing=True,
        ) is False
        row = conn.execute("SELECT status, source FROM runs WHERE run_id='web-run'").fetchone()
        assert row == ("RUNNING", "WEB")
    finally:
        conn.close()


def test_progress_merge_preserves_existing_metadata(tmp_path):
    import json
    from dealhunter.run_lifecycle import update_run_progress

    db_path = str(tmp_path / "runs-progress.db")
    conn = setup_db(db_path)
    try:
        conn.execute(
            """INSERT INTO runs (run_id, started_at, status, run_metadata)
               VALUES ('progress-run', CURRENT_TIMESTAMP, 'RUNNING', ?)""",
            (json.dumps({"existing": {"keep": True}}),),
        )
        conn.commit()

        assert update_run_progress(
            conn,
            "progress-run",
            phase="CRAWLING",
            completed=2,
            total=5,
            unit="tiendas",
        )
        raw = conn.execute(
            "SELECT run_metadata FROM runs WHERE run_id='progress-run'"
        ).fetchone()[0]
        metadata = json.loads(raw)
        assert metadata["existing"] == {"keep": True}
        assert metadata["progress"]["phase"] == "CRAWLING"
        assert metadata["progress"]["completed"] == 2
        assert metadata["progress"]["total"] == 5
        assert metadata["progress"]["unit"] == "tiendas"
        assert metadata["progress"]["updated_at"]
        assert metadata["progress"]["phase_started_at"]
    finally:
        conn.close()


def test_active_run_authority_ignores_historical_running(tmp_path):
    from dealhunter.run_lifecycle import find_active_run

    db_path = str(tmp_path / "runs-active.db")
    conn = setup_db(db_path)
    try:
        conn.execute(
            """INSERT INTO runs (run_id, started_at, status)
               VALUES ('old-running', datetime('now', '-3 hours'), 'RUNNING')"""
        )
        conn.commit()
        assert find_active_run(conn) is None

        assert reserve_run(
            conn, "fresh-run", lat=1.0, lng=2.0, radius=5.0, source="WEB"
        ) is True
        active = find_active_run(conn)
        assert active[0] == "fresh-run"
    finally:
        conn.close()


def test_reserve_run_persists_starting_progress(tmp_path):
    import json

    db_path = str(tmp_path / "runs-starting.db")
    conn = setup_db(db_path)
    try:
        reserve_run(conn, "start-run", lat=1.0, lng=2.0, radius=5.0, source="WEB")
        raw = conn.execute(
            "SELECT run_metadata FROM runs WHERE run_id='start-run'"
        ).fetchone()[0]
        progress = json.loads(raw)["progress"]
        assert progress["phase"] == "STARTING"
        assert progress["completed"] == 0
        assert progress["total"] is None
    finally:
        conn.close()
