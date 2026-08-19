import os
import sys
import tempfile
import sqlite3
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from dealhunter.web.app import create_app
from dealhunter.db import setup_db

@pytest.fixture
def app():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    
    conn = setup_db(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('r1', 'McDonalds', 'restaurants')")
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('s1', 'Soriana', 'market')")
    
    # Dish available with base price and toppings
    c.execute("INSERT INTO products (product_id, store_id, name, category, has_toppings) VALUES ('d1', 'r1', 'Combo McTrio Elige tu gusto', 'Combos', 1)")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, availability) VALUES ('1', 'r1', 'd1', 120.0, '2026-08-01T00:00:00', 'AVAILABLE')")
    
    # Dish unavailable with direct discount
    c.execute("INSERT INTO products (product_id, store_id, name, category, has_toppings) VALUES ('d2', 'r1', 'Papas Grandes', 'Extras', 0)")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, discount_effective, promotion_label, timestamp, availability) VALUES ('1', 'r1', 'd2', 30.0, 50.0, 20.0, 'Directo', '2026-08-01T00:00:00', 'UNAVAILABLE')")
    
    # Dish without category
    c.execute("INSERT INTO products (product_id, store_id, name, category, has_toppings) VALUES ('d3', 'r1', 'Helado Sencillo', NULL, NULL)")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, availability) VALUES ('1', 'r1', 'd3', 20.0, '2026-08-01T00:00:00', 'AVAILABLE')")
    
    conn.commit()
    conn.close()
    
    app = create_app({'DATABASE': db_path, 'TESTING': True})
    yield app
    os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_restaurants_home(client):
    rv = client.get('/restaurants')
    assert rv.status_code == 200
    assert b'McDonalds' in rv.data
    assert b'Soriana' not in rv.data
    assert b'3' in rv.data # total dishes

def test_restaurant_detail(client):
    rv = client.get('/restaurants/r1')
    assert rv.status_code == 200
    assert b'McDonalds' in rv.data
    assert b'Combos' in rv.data
    assert b'Extras' in rv.data
    assert b'Otros' in rv.data # For Helado Sencillo

def test_restaurant_detail_not_found(client):
    rv = client.get('/restaurants/invalid')
    assert rv.status_code == 404

def test_search_global_types(client):
    rv = client.get('/search?q=McD')
    assert rv.status_code == 200
    assert b'McDonalds' in rv.data
    assert b'Restaurante' in rv.data

def test_category_semantics(client):
    rv = client.get('/categories')
    assert rv.status_code == 200
    assert b'Combos' in rv.data
    assert b'Extras' in rv.data
    assert b'Uncategorized' in rv.data

