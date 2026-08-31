from dealhunter.run_status import normalize_run_status
from dealhunter.web.queries import search_local, get_restaurants_home, get_product_compare

import pytest
import os
import tempfile
import sqlite3
from dealhunter.db import setup_db
from dealhunter.web.app import create_app

@pytest.fixture
def app():
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    setup_db(db_path)
    # create default config tables
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO runs (run_id, status) VALUES ('default_run', 'SUCCESS')")
    conn.commit()
    conn.close()
    
    app = create_app({'DATABASE': db_path, 'TESTING': True, 'SECRET_KEY': 'test'})
    yield app
    os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()



def test_normalize_run_status():
    assert normalize_run_status("COMPLETE") == "SUCCESS"
    assert normalize_run_status("COMPLETED") == "SUCCESS"
    assert normalize_run_status("SUCCESS") == "SUCCESS"
    assert normalize_run_status("PARTIAL") == "PARTIAL"
    assert normalize_run_status("REQUEST_BUDGET_REACHED") == "PARTIAL"
    assert normalize_run_status("TIMEOUT") == "PARTIAL"
    assert normalize_run_status("FAILED") == "FAILED"
    assert normalize_run_status("ERROR") == "FAILED"
    assert normalize_run_status("RUNNING") == "RUNNING"
    assert normalize_run_status(None) == "FAILED"

def test_trusted_view_historical_compatibility():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    
    conn = setup_db(tmp.name)
    c = conn.cursor()
    
    # Create runs
    runs = [
        ("r_success", "SUCCESS"),
        ("r_completed", "COMPLETED"),
        ("r_complete", "COMPLETE"),
        ("r_partial", "PARTIAL"),
        ("r_running", "RUNNING"),
        ("r_failed", "FAILED"),
        ("r_error", "ERROR")
    ]
    for rid, st in runs:
        c.execute("INSERT INTO runs (run_id, status) VALUES (?, ?)", (rid, st))
        c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES (?, 'rappi', 's1', ?, 10)", (rid, rid + "_p"))
        
    # Orphan
    c.execute("INSERT INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r_orphan', 'rappi', 's1', 'orphan_p', 10)")
    
    conn.commit()
    
    # Check trusted
    c.execute("SELECT run_id FROM trusted_observations")
    trusted = {r[0] for r in c.fetchall()}
    
    assert "r_success" in trusted
    assert "r_completed" in trusted
    assert "r_complete" in trusted
    assert "r_partial" in trusted
    
    assert "r_running" not in trusted
    assert "r_failed" not in trusted
    assert "r_error" not in trusted
    assert "r_orphan" not in trusted
    
    conn.close()
    os.unlink(tmp.name)

def test_category_none_price(client, app):
    # Setup a product with None price
    with app.app_context():
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO stores (provider, store_id, name, type) VALUES ('rappi', 's1', 'Store 1', 'market')")
        c.execute("INSERT OR IGNORE INTO runs (run_id, status) VALUES ('r1', 'SUCCESS')")
        c.execute("INSERT OR IGNORE INTO products (provider, store_id, product_id, name, category) VALUES ('rappi', 's1', 'p_none', 'Product None', 'cat1')")
        c.execute("INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r1', 'rappi', 's1', 'p_none', NULL)")
        conn.commit()
        conn.close()
        
    resp = client.get('/categories/cat1')
    assert resp.status_code == 200
    assert b"Product None" in resp.data
    # "—" or similar should be rendered, not crashing
    assert b"&#34;" not in resp.data # Ensure no syntax errors

def test_compare_free_null_store(client, app):
    # Setup product with NULL store_name
    with app.app_context():
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO runs (run_id, status) VALUES ('r1', 'SUCCESS')")
        c.execute("INSERT OR IGNORE INTO stores (provider, store_id, type) VALUES ('rappi', 's_null', 'market')") # name is NULL
        c.execute("INSERT OR IGNORE INTO products (provider, store_id, product_id, name) VALUES ('rappi', 's_null', 'p_pizza', 'Pizza Margarita')")
        c.execute("INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, price) VALUES ('r1', 'rappi', 's_null', 'p_pizza', 10)")
        conn.commit()
        conn.close()
        
    resp = client.get('/compare?q=Pizza')
    assert resp.status_code == 200
    assert b"Desconocida" in resp.data or b"s_null" in resp.data

def test_admin_catalog_sync_init_error(client, app):
    resp = client.get('/admin/catalog-sync')
    assert resp.status_code == 200
    assert b"catalog-sync" in resp.data.lower()

def test_uber_restaurants_included(app):
    with app.app_context():
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO stores (provider, store_id, name, type, vertical) VALUES ('uber_eats', 'u_rest', 'Uber Rest', 'RESTAURANT', NULL)")
        c.execute("INSERT OR IGNORE INTO products (provider, store_id, product_id, name) VALUES ('uber_eats', 'u_rest', 'p1', 'Dish')")
        c.execute("INSERT OR IGNORE INTO runs (run_id, status) VALUES ('r1', 'SUCCESS')")
        c.execute("INSERT OR IGNORE INTO observations (run_id, provider, store_id, product_id, price, availability) VALUES ('r1', 'uber_eats', 'u_rest', 'p1', 10, 'AVAILABLE')")
        conn.commit()
        
        rests = get_restaurants_home(app.config['DATABASE'])
        found = any(r["store_id"] == "u_rest" for r in rests)
        assert found, "Uber restaurant with type RESTAURANT and vertical NULL must be included"
        conn.close()
