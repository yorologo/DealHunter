import os
import sys
import tempfile
import sqlite3
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from dealhunter.web.app import create_app
from dealhunter.db import setup_db

@pytest.fixture
def app():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    
    conn = setup_db(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'Soriana', '', 'market')")
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s2', 'Turbo Store', '', 'chiper_home')")
    
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_quantity, normalized_unit, category) VALUES ('p1', 's1', 'Prod 1', 1, 'L', 'bebidas')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_quantity, normalized_unit, category) VALUES ('p2', 's2', 'Prod 2', 1, 'L', 'farmacia')")
    
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, query_term) VALUES ('r1', 's1', 'p1', 30.0, '2026-08-01T00:00:00', 'bebidas')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, query_term) VALUES ('r2', 's1', 'p1', 25.0, '2026-08-02T00:00:00', 'bebidas')")
    
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, query_term) VALUES ('r1', 's2', 'p2', 50.0, '2026-08-01T00:00:00', 'farmacia')")
    
    conn.commit()
    conn.close()
    
    app = create_app({'DATABASE': db_path, 'TESTING': True})
    yield app
    os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_deals_page(client):
    rv = client.get('/deals')
    assert rv.status_code == 200
    assert b'Oportunidades' in rv.data

def test_market_page(client):
    rv = client.get('/market')
    assert rv.status_code == 200
    assert b'Supermercados' in rv.data
    assert b'Prod 1' in rv.data
    assert b'Prod 2' not in rv.data

def test_turbo_page(client):
    rv = client.get('/turbo')
    assert rv.status_code == 200
    assert b'Turbo' in rv.data
    assert b'Prod 2' in rv.data
    assert b'Prod 1' not in rv.data

def test_categories_page(client):
    rv = client.get('/categories')
    assert rv.status_code == 200
    assert b'bebidas' in rv.data
    assert b'farmacia' in rv.data

def test_category_detail(client):
    rv = client.get('/categories/bebidas')
    assert rv.status_code == 200
    assert b'Prod 1' in rv.data
    assert b'Prod 2' not in rv.data

def test_stores_page(client):
    rv = client.get('/stores')
    assert rv.status_code == 200
    assert b'Soriana' in rv.data
    assert b'Turbo Store' in rv.data

def test_store_detail(client):
    rv = client.get('/stores/s1')
    assert rv.status_code == 200
    assert b'Soriana' in rv.data
    assert b'Prod 1' in rv.data

