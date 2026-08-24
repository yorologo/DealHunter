import pytest
import sqlite3
from dealhunter.web.app import create_app

@pytest.fixture
def app_and_db(tmp_path):
    db_path = str(tmp_path / 'test.db')
    from dealhunter.db import setup_db
    setup_db(db_path)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('STORE1', 'Empty Store', 'restaurant')")
    c.execute("INSERT INTO stores (store_id, name, type) VALUES ('STORE2', 'Full Store', 'market')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('P1', 'STORE2', 'Prod 1')")
    conn.commit()
    conn.close()
    
    app = create_app({'TESTING': True, 'DATABASE': db_path, 'SECRET_KEY': 'dev'})
    yield app, db_path

def test_stores_index_hides_empty(app_and_db):
    app, db_path = app_and_db
    with app.test_client() as c:
        response = c.get('/stores')
        html = response.get_data(as_text=True)
        assert 'Full Store' in html
        assert 'Empty Store' not in html

def test_stores_index_shows_all_with_flag(app_and_db):
    app, db_path = app_and_db
    with app.test_client() as c:
        response = c.get('/stores?all=1')
        html = response.get_data(as_text=True)
        assert 'Full Store' in html
        assert 'Empty Store' in html

def test_store_detail_empty_state(app_and_db):
    app, db_path = app_and_db
    with app.test_client() as c:
        response = c.get('/stores/STORE1')
        html = response.get_data(as_text=True)
        assert 'Esta tienda aún no tiene datos suficientes' in html

def test_store_detail_full_state(app_and_db):
    app, db_path = app_and_db
    with app.test_client() as c:
        response = c.get('/stores/STORE2')
        html = response.get_data(as_text=True)
        assert 'Esta tienda aún no tiene datos suficientes' not in html
        assert 'catalog-grid' in html

def test_product_card_strike_through_formatting(app_and_db):
    app, db_path = app_and_db
    # To test template logic, we need to pass a product dictionary to the template context.
    # Flask allows `render_template_string` or we can just fetch the store catalog.
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Add a product with metrics (original price)
    
    # update products table for the catalog to fetch it properly
    # Actually wait, inserting raw DB rows to satisfy the entire query layer for `catalog` is complex.
    # We can just use `render_template` directly within request context.
    conn.commit()
    conn.close()

    from flask import render_template_string
    with app.test_request_context('/'):
        # Mock product
        p = {
            "store_id": "STORE2", "product_id": "P1", "store_name": "Full Store",
            "product_name": "Prod 1", "current_price": 50.0,
            "metrics": {"original_price": 100.0, "deal_status": "REAL_DEAL", "is_suspicious_reference": False}
        }
        
        # Include the macro and then render the card
        html = render_template_string('''
        {% set item = p %}
        {% include "components/product_card.html" %}
        ''', p=p)
        
        # It should render the strike-through without literal markdown tildes
        assert '~$100.00~' not in html
        assert '$100.00' in html
        assert 'text-decoration-line-through' in html
