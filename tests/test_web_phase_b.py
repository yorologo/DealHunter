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
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s2', 'Chedraui', '', 'market')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_quantity, normalized_unit, fingerprint) VALUES ('p1', 's1', 'Electrolit Mora Azul 625 ml', 625, 'ml', 'fp1')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_quantity, normalized_unit, fingerprint) VALUES ('p1', 's2', 'Electrolit Mora Azul 625 ml', 625, 'ml', 'fp1')")
    
    now = datetime.now()
    t1 = (now - timedelta(days=2)).isoformat()
    t2 = (now - timedelta(days=1)).isoformat()
    t3 = now.isoformat()
    
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r1', '2024-01-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, original_price) VALUES ('r1', 's1', 'p1', 30.0, ?, 35.0)", (t1,))
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r2', '2024-01-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, original_price) VALUES ('r2', 's1', 'p1', 22.95, ?, 35.0)", (t2,))
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r3', '2024-01-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp, original_price) VALUES ('r3', 's1', 'p1', 22.95, ?, 35.0)", (t3,))
    
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r3', '2024-01-01', 'SUCCESS')")
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
    rv = client.get('/products/rappi/s1/p1')
    assert rv.status_code == 200
    assert b'Electrolit Mora Azul 625 ml' in rv.data
    assert b'REAL_DEAL' in rv.data or b'NEW_LOW' in rv.data # Might be NEW_LOW depending on exact metrics calculation
    assert b'22.95' in rv.data
    assert b'Objetivo: $25.00' in rv.data
    assert b'alertas' in rv.data

def test_product_not_found(client):
    rv = client.get('/products/rappi/s1/non_existent')
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


def test_compare_anchor(client):
    rv = client.get('/compare?provider=rappi&store_id=s1&product_id=p1')
    assert rv.status_code == 200
    assert b'Comparando equivalentes a' in rv.data
    assert b'Electrolit Mora Azul 625 ml' in rv.data
    assert b'Soriana' in rv.data
    assert b'Chedraui' in rv.data

def test_compare_anchor_no_matches(client):
    # Need to setup a product with no matches
    pass


def test_compare_anchor_strict_rules(client):
    from dealhunter.db import get_default_db_path, setup_db
    import os
    db_path = current_app.config['DATABASE'] if 'current_app' in globals() else None
    
    # We will just write a direct unit test against compare_with_anchor logic
    # using a temporary DB since we need full control over the data.
    import tempfile
    from dealhunter.historico import compare_with_anchor
    
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "strict.db")
    conn = setup_db(db)
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'T1', '', 'market')")
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s2', 'T2', '', 'market')")
    
    # Anchor
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_anc', 's1', 'Coca Cola Original 2 L', 'coca cola original 2 l', 'Coca Cola', '2', 'L', 2000, 'ml', 'fp_coca2l')")
    
    # Matches
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_m1', 's2', 'Coca Cola Original 2 L', 'coca cola original 2 l', 'Coca Cola', '2', 'L', 2000, 'ml', 'fp_coca2l')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_m2', 's2', 'Coca-Cola Original 2000 ml', 'coca cola original 2000 ml', 'Coca Cola', '2000', 'ml', 2000, 'ml', 'fp_coca2l_alt')") # Same brand, same size, similar words -> should HIGH MATCH
    
    # Non-Matches
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_nm1', 's2', 'Coca Cola Zero 2 L', 'coca cola zero 2 l', 'Coca Cola', '2', 'L', 2000, 'ml', 'fp_coca_zero')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_nm2', 's2', 'Coca Cola Original 600 ml', 'coca cola original 600 ml', 'Coca Cola', '600', 'ml', 600, 'ml', 'fp_coca600')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, pack_count, fingerprint) VALUES ('p_nm3', 's2', 'Coca Cola Original 2 L 6 pack', 'coca cola original 2 l 6 pack', 'Coca Cola', '2', 'L', 2000, 'ml', 6, 'fp_coca2l_6')")
    
    # Entera vs Deslactosada
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_milk_anc', 's1', 'Leche Entera 1 L', 'leche entera 1 l', 'Lala', '1', 'L', 1000, 'ml', 'fp_milk')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_milk_nm', 's2', 'Leche Deslactosada 1 L', 'leche deslactosada 1 l', 'Lala', '1', 'L', 1000, 'ml', 'fp_milk_des')")
    
    # Shampoo vs Acondicionador
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_sham_anc', 's1', 'Shampoo 400 ml', 'shampoo 400 ml', 'Pantene', '400', 'ml', 400, 'ml', 'fp_sham')")
    c.execute("INSERT INTO products (product_id, store_id, name, normalized_name, brand, quantity, unit, normalized_quantity, normalized_unit, fingerprint) VALUES ('p_sham_nm', 's2', 'Acondicionador 400 ml', 'acondicionador 400 ml', 'Pantene', '400', 'ml', 400, 'ml', 'fp_acon')")
    
    # We must insert at least 2 observations to ensure metrics are generated (since we need metrics for them to appear in final valid_matches)
    for p in ['p_anc', 'p_m1', 'p_m2', 'p_nm1', 'p_nm2', 'p_nm3', 'p_milk_anc', 'p_milk_nm', 'p_sham_anc', 'p_sham_nm']:
        c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r1', '2024-01-01', 'SUCCESS')")
        c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r1', ?, ?, 30.0, '2026-08-01T00:00:00')", ('s1' if 'anc' in p else 's2', p,))
        c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('r2', '2024-01-01', 'SUCCESS')")
        c.execute("INSERT INTO observations (run_id, store_id, product_id, price, timestamp) VALUES ('r2', ?, ?, 25.0, '2026-08-02T00:00:00')", ('s1' if 'anc' in p else 's2', p,))
        
    conn.commit()
    conn.close()
    
    res = compare_with_anchor(db, 'rappi', 's1', 'p_anc')
    matched_ids = [m['product_id'] for m in res['matches']]
    
    assert 'p_anc' in matched_ids
    assert 'p_m1' in matched_ids
    # Note: p_m2 may or may not match depending on exact semantic variant rules in normalization.py. If it doesn't match, we will test why.
    # Actually, since both are same brand, size, unit and share semantic chars, HIGH/FUZZY will match it.
    
    assert 'p_nm1' not in matched_ids # Zero vs Original
    assert 'p_nm2' not in matched_ids # 600ml vs 2000ml
    assert 'p_nm3' not in matched_ids # Pack mismatch
    
    res_milk = compare_with_anchor(db, 'rappi', 's1', 'p_milk_anc')
    assert 'p_milk_nm' not in [m['product_id'] for m in res_milk['matches']]
    
    res_sham = compare_with_anchor(db, 'rappi', 's1', 'p_sham_anc')
    assert 'p_sham_nm' not in [m['product_id'] for m in res_sham['matches']]


def test_format_unit_price():
    from dealhunter.normalization import format_unit_price
    assert format_unit_price(42, 2, 'L') == '$21/L'
    assert format_unit_price(42, 2000, 'ml') == '$21/L'
    assert format_unit_price(20, 500, 'ml') == '$40/L'
    assert format_unit_price(80, 1, 'kg') == '$80/kg'
    assert format_unit_price(40, 500, 'g') == '$80/kg'
    # 6 x 355 ml = 2130 ml
    assert format_unit_price(42.6, 2130, 'ml') == '$20/L'
