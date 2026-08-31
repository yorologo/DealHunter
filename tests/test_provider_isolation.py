import pytest
import sqlite3
import os
import tempfile
from dealhunter.db import setup_db

def test_adversarial_provider_isolation():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "isolation.db")
    
    # 1. Setup V15 Schema
    setup_db(db_path)
    
    # We will just use raw SQL for the adversarial test to be perfectly clear what is happening
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 2. Insert Rappi store and product
    c.execute("INSERT INTO stores (provider, store_id, name) VALUES ('rappi', 's1', 'Rappi Store')")
    c.execute("INSERT INTO products (provider, product_id, store_id, name) VALUES ('rappi', 'p1', 's1', 'Rappi Product')")
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r_run', '2024-01-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r_run', 'rappi', 's1', 'p1', 100.0)")
    
    # 3. Insert Uber Eats store and product with EXACT SAME IDs
    c.execute("INSERT INTO stores (provider, store_id, name) VALUES ('uber_eats', 's1', 'Uber Store')")
    c.execute("INSERT INTO products (provider, product_id, store_id, name) VALUES ('uber_eats', 'p1', 's1', 'Uber Product')")
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('u_run', '2024-01-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('u_run', 'uber_eats', 's1', 'p1', 200.0)")
    
    conn.commit()
    
    # 4. Assert isolation
    c.execute("SELECT provider, name FROM stores ORDER BY provider ASC")
    stores = c.fetchall()
    assert len(stores) == 2
    assert stores[0] == ("rappi", "Rappi Store")
    assert stores[1] == ("uber_eats", "Uber Store")
    
    c.execute("SELECT provider, name FROM products ORDER BY provider ASC")
    products = c.fetchall()
    assert len(products) == 2
    assert products[0] == ("rappi", "Rappi Product")
    assert products[1] == ("uber_eats", "Uber Product")
    
    c.execute("SELECT provider, price FROM observations ORDER BY provider ASC")
    obs = c.fetchall()
    assert len(obs) == 2
    assert obs[0] == ("rappi", 100.0)
    assert obs[1] == ("uber_eats", 200.0)
    
    conn.close()

