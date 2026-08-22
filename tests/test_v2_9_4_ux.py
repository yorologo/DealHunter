import pytest
import sqlite3
from dealhunter.web.app import create_app
from dealhunter.web.queries import get_catalog

@pytest.fixture
def app_client(tmp_path):
    from dealhunter.db import setup_db
    db_path = str(tmp_path / 'test.db')
    setup_db(db_path)
    
    # Populate a little data
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('popeyes_1', 'Popeyes 1', 'restaurants')")
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('other_1', 'Other 1', 'market')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p1', 'popeyes_1', 'Burger')")
    c.execute("INSERT INTO observations (product_id, store_id, timestamp, price, original_price) VALUES ('p1', 'popeyes_1', '2026-08-22 12:00:00', 10, 10)")
    conn.commit()
    conn.close()
    
    app = create_app()
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client, db_path

def test_unverified_account_can_replace_session(app_client):
    client, db_path = app_client
    from unittest.mock import patch
    with patch('dealhunter.account.get_account_status') as m:
        m.return_value = {
            'status': 'UNVERIFIED',
            'configured': True,
            'source': 'PERSISTENT',
            'last_validated_at': '2026-08-22T19:00:00Z',
            'effective': True
        }
        res = client.get('/admin/account')
        html = res.data.decode('utf-8')
        assert 'btn-primary' in html
        assert 'Reemplazar sesión' in html
        assert 'disabled' not in html[html.find('Reemplazar sesión') - 100:html.find('Reemplazar sesión')]

def test_restaurant_empty_state_filtered(app_client):
    client, db_path = app_client
    res = client.get('/restaurants?only_deals=1', headers={'HX-Request': 'true'})
    html = res.data.decode('utf-8')
    assert 'No hay productos que coincidan con los filtros seleccionados' in html
    assert 'Limpiar filtros' in html

def test_restaurant_empty_state_no_data(app_client):
    client, db_path = app_client
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM observations")
    conn.execute("DELETE FROM products")
    conn.commit()
    conn.close()
    
    res = client.get('/restaurants', headers={'HX-Request': 'true'})
    html = res.data.decode('utf-8')
    assert 'Aún no hay productos capturados' in html
    assert 'Limpiar filtros' not in html

def test_restaurant_filtered_result_count(app_client):
    client, db_path = app_client
    filters = {"vertical": "restaurants", "only_deals": True}
    data = get_catalog(db_path, filters, "discount", 1)
    assert data["total"] == 0
    
    res = client.get('/restaurants?only_deals=1', headers={'HX-Request': 'true'})
    html = res.data.decode('utf-8')
    assert '0 resultados' in html

def test_clear_restaurant_filters(app_client):
    client, db_path = app_client
    res = client.get('/restaurants?store=popeyes_1&category=test&only_deals=1', headers={'HX-Request': 'true'})
    html = res.data.decode('utf-8')
    assert 'Limpiar filtros' in html
    assert 'href="/restaurants?sort=discount&vertical=restaurants"' in html.replace('amp;', '')
