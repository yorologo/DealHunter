import pytest
from dealhunter.web.admin_queries import get_run_detail, get_runs_paginated
import sqlite3

@pytest.fixture
def db_conn(tmp_path):
    from dealhunter.db import setup_db
    db_path = str(tmp_path / 'test.db')
    setup_db(db_path)
    return db_path

def test_timestamp_not_double_converted(db_conn):
    conn = sqlite3.connect(db_conn)
    conn.execute("INSERT INTO runs (run_id, started_at) VALUES ('123', '2026-08-22 18:32:56')")
    conn.commit()
    
    run = get_run_detail(db_conn, '123')
    assert run['started_at'] == '2026-08-22 18:32:56'
    
def test_stale_running_run_handling(db_conn):
    conn = sqlite3.connect(db_conn)
    conn.execute("INSERT INTO runs (run_id, status, started_at) VALUES ('new_run', 'RUNNING', datetime('now'))")
    conn.execute("INSERT INTO runs (run_id, status, started_at) VALUES ('stale_run', 'RUNNING', datetime('now', '-3 hours'))")
    conn.commit()
    
    get_runs_paginated(db_conn)
    
    cur = conn.cursor()
    cur.execute("SELECT status FROM runs WHERE run_id = 'new_run'")
    assert cur.fetchone()[0] == 'RUNNING'
    
    cur.execute("SELECT status FROM runs WHERE run_id = 'stale_run'")
    # We no longer mutate the database on GET
    assert cur.fetchone()[0] == 'RUNNING'


def test_run_counts_use_provider_aware_identity(db_conn):
    conn = sqlite3.connect(db_conn)
    conn.execute(
        "INSERT INTO runs (run_id, status, started_at) VALUES ('multi', 'COMPLETED', '2026-08-22 18:32:56')"
    )
    conn.execute(
        "INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('multi', 'rappi', 'shared', 'same', 10)"
    )
    conn.execute(
        "INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('multi', 'uber_eats', 'shared', 'same', 20)"
    )
    conn.commit()
    conn.close()

    run = get_run_detail(db_conn, 'multi')
    assert run['observation_count'] == 2
    assert run['product_count'] == 2
    assert run['store_count'] == 2
