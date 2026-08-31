import pytest
import sqlite3
import tempfile
import os
from dealhunter.db import setup_db
from dealhunter.web.app import create_app

def create_stale_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Mock a schema version 16
    c.execute('CREATE TABLE schema_version (version INTEGER)')
    c.execute('INSERT INTO schema_version (version) VALUES (16)')
    c.execute('CREATE TABLE runs (run_id TEXT PRIMARY KEY, status TEXT)')
    c.execute('CREATE TABLE observations (run_id TEXT, provider TEXT, store_id TEXT, product_id TEXT, price REAL)')
    
    # Create the OLD stale view
    c.execute('''
        CREATE VIEW trusted_observations AS 
        SELECT * FROM observations 
        WHERE provider IN ('rappi', 'uber_eats') 
          AND (run_id IN (SELECT run_id FROM runs) OR run_id = 'run_d8c5dbb90f34') 
          AND run_id != 'test_run_123'
    ''')
    conn.commit()
    conn.close()

def test_stale_view_upgrade():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "stale.db")
    create_stale_db(db_path)
    
    # Run setup_db to simulate app startup
    setup_db(db_path)
    
    # Verify the view is upgraded
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='trusted_observations'")
    sql = c.fetchone()[0]
    
    assert "r.status IN ('SUCCESS', 'PARTIAL')" in sql
    assert "test_run_123" not in sql
    conn.close()

def test_trusted_view_semantics():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "fresh.db")
    setup_db(db_path)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # SUCCESS run
    c.execute("INSERT INTO runs (run_id, status) VALUES ('r_succ', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, provider, product_id) VALUES ('r_succ', 'rappi', 'p_succ')")
    
    # PARTIAL run
    c.execute("INSERT INTO runs (run_id, status) VALUES ('r_part', 'PARTIAL')")
    c.execute("INSERT INTO observations (run_id, provider, product_id) VALUES ('r_part', 'rappi', 'p_part')")
    
    # FAILED run
    c.execute("INSERT INTO runs (run_id, status) VALUES ('r_fail', 'FAILED')")
    c.execute("INSERT INTO observations (run_id, provider, product_id) VALUES ('r_fail', 'rappi', 'p_fail')")
    
    # RUNNING run
    c.execute("INSERT INTO runs (run_id, status) VALUES ('r_run', 'RUNNING')")
    c.execute("INSERT INTO observations (run_id, provider, product_id) VALUES ('r_run', 'rappi', 'p_run')")
    
    # Orphan
    c.execute("INSERT INTO observations (run_id, provider, product_id) VALUES ('orphan', 'rappi', 'p_orph')")
    
    # Invalid provider
    c.execute("INSERT INTO runs (run_id, status) VALUES ('r_inv', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, provider, product_id) VALUES ('r_inv', 'invalid', 'p_inv')")
    
    conn.commit()
    
    c.execute("SELECT product_id FROM trusted_observations")
    pids = {row[0] for row in c.fetchall()}
    
    assert 'p_succ' in pids
    assert 'p_part' in pids
    assert 'p_fail' not in pids
    assert 'p_run' not in pids
    assert 'p_orph' not in pids
    assert 'p_inv' not in pids
    
    conn.close()

def test_restaurant_badges():
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "badge.db")
    conn = setup_db(db_path)
    c = conn.cursor()
    
    # Rappi restaurant
    c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('rappi', 'r1', 'Rappi Rest', 'restaurant')")
    
    # Uber Eats restaurant
    c.execute("INSERT INTO stores (provider, store_id, name, type) VALUES ('uber_eats', 'u1', 'Uber Rest', 'restaurant')")
    
    conn.commit()
    conn.close()
    
    app = create_app({"DATABASE": db_path, "SECRET_KEY": "test"})
    client = app.test_client()
    
    res_r = client.get('/restaurants/rappi/r1')
    html_r = res_r.data.decode('utf-8')
    assert "Rappi</span>" in html_r
    assert "rappi-launcher" in html_r
    assert "Abrir en Rappi" in html_r
    
    res_u = client.get('/restaurants/uber_eats/u1')
    html_u = res_u.data.decode('utf-8')
    assert "Uber Eats</span>" in html_u
    assert "rappi-launcher" not in html_u
    assert "Abrir en Rappi" not in html_u

