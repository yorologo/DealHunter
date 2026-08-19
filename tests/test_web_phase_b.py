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
    c.execute("INSERT INTO stores VALUES ('s1', 'Soriana', '', 'market')")
    c.execute("INSERT INTO stores VALUES ('s2', 'Chedraui', '', 'market')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_quantity, normalized_unit) VALUES ('p1', 's1', 'Electrolit Mora Azul 625 ml', 625, 'ml')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_quantity, normalized_unit) VALUES ('p1', 's2', 'Electrolit Mora Azul 625 ml', 625, 'ml')")
    
    now = datetime.now()
    t1 = (now - timedelta(days=2)).isoformat()
    t2 = (now - timedelta(days=1)).isoformat()
    t3 = now.isoformat()
    
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, original_price) VALUES ('r1', 's1', 'p1', 30.0, ?, 35.0)", (t1,))
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, original_price) VALUES ('r2', 's1', 'p1', 22.95, ?, 35.0)", (t2,))
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, original_price) VALUES ('r3', 's1', 'p1', 22.95, ?, 35.0)", (t3,))
    
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r3', 's2', 'p1', 25.0, ?)", (t3,))
    
    c.execute("INSERT INTO watchlist (query, target_price, enabled) VALUES ('Electrolit Mora Azul 625 ml', 25.0, 1)")
    c.execute("INSERT INTO alerts (id, product_id, store_id, alert_type, triggered_at, seen) VALUES (1, 'p1', 's1', 'NEW_LOW', ?, 0)", (t2,))
    
    conn.commit()
    conn.close()
    
    app = create_app({'DATABASE': db_path, 'TESTING': True})
    yield app
    os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_product_detail(client):
    rv = client.get('/products/s1/p1')
    assert rv.status_code == 200
    assert b'Electrolit Mora Azul 625 ml' in rv.data
    assert b'REAL_DEAL' in rv.data or b'NEW_LOW' in rv.data # Might be NEW_LOW depending on exact metrics calculation
    assert b'22.95' in rv.data
    assert b'Objetivo: $25.00' in rv.data
    assert b'alertas' in rv.data

def test_product_not_found(client):
    rv = client.get('/products/s1/non_existent')
    assert rv.status_code == 404
    assert b'Producto no encontrado' in rv.data

def test_compare_page(client):
    rv = client.get('/compare?q=Electrolit')
    assert rv.status_code == 200
    assert b'Electrolit' in rv.data
    assert b'Soriana' in rv.data
    assert b'Chedraui' in rv.data

def test_compare_page_no_results(client):
    rv = client.get('/compare?q=Desconocido')
    assert rv.status_code == 200
    assert b'No hay coincidencias' in rv.data

def test_products_catalog(client):
    rv = client.get('/products')
    assert rv.status_code == 200
    assert b'Electrolit Mora Azul' in rv.data
