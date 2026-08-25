import pytest
import sqlite3
import os
import tempfile
from datetime import datetime
from dealhunter.db import setup_db

def setup_test_db():
    test_db = os.path.join(tempfile.gettempdir(), "test_provider_collision.db")
    if os.path.exists(test_db):
        os.remove(test_db)
    conn = setup_db(test_db)
    return test_db, conn

def test_provider_collision_store():
    db_path, conn = setup_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO stores (provider, store_id, name) VALUES ('rappi', 'COLLISION', 'Rappi Store')")
    c.execute("INSERT INTO stores (provider, store_id, name) VALUES ('uber_eats', 'COLLISION', 'Uber Store')")
    conn.commit()
    
    c.execute("SELECT name FROM stores WHERE store_id = 'COLLISION' ORDER BY provider ASC")
    rows = c.fetchall()
    assert len(rows) == 2
    assert rows[0][0] == 'Rappi Store'  # provider='rappi' is first alphabetically
    assert rows[1][0] == 'Uber Store'
    conn.close()

def test_provider_collision_product():
    db_path, conn = setup_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO products (provider, store_id, product_id, name) VALUES ('rappi', 's1', 'SAME', 'Rappi Prod')")
    c.execute("INSERT INTO products (provider, store_id, product_id, name) VALUES ('uber_eats', 's1', 'SAME', 'Uber Prod')")
    conn.commit()
    
    c.execute("SELECT name FROM products WHERE product_id = 'SAME' ORDER BY provider ASC")
    rows = c.fetchall()
    assert len(rows) == 2
    assert rows[0][0] == 'Rappi Prod'
    assert rows[1][0] == 'Uber Prod'
    conn.close()

def test_provider_history_isolation():
    db_path, conn = setup_test_db()
    c = conn.cursor()
    c.execute("INSERT INTO observations (provider, run_id, store_id, product_id, price, timestamp) VALUES ('rappi', 'r1', 's1', 'p1', 100, '2024-01-01T10:00:00Z')")
    c.execute("INSERT INTO observations (provider, run_id, store_id, product_id, price, timestamp) VALUES ('rappi', 'r2', 's1', 'p1', 120, '2024-01-01T12:00:00Z')")
    c.execute("INSERT INTO observations (provider, run_id, store_id, product_id, price, timestamp) VALUES ('uber_eats', 'r3', 's1', 'p1', 80, '2024-01-01T14:00:00Z')")
    conn.commit()
    
    # Simulate latest observation query by partition
    c.execute('''SELECT provider, price FROM (
                    SELECT provider, price, ROW_NUMBER() OVER (PARTITION BY provider, store_id, product_id ORDER BY timestamp DESC) as rn
                    FROM observations
                 ) WHERE rn = 1 ORDER BY provider ASC''')
    rows = c.fetchall()
    assert len(rows) == 2
    assert rows[0] == ('rappi', 120.0)
    assert rows[1] == ('uber_eats', 80.0)
    conn.close()

