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
