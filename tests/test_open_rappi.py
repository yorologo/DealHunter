import pytest
import sys, os
import sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dealhunter.web.app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True, "DATABASE": "test_open_rappi.db"})
    with app.app_context():
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS stores (store_id TEXT, name TEXT, type TEXT)")
        c.execute("INSERT INTO stores VALUES ('111', 'McDonalds', 'restaurant')")
        c.execute("INSERT INTO stores VALUES ('222', 'Chedraui', 'market')")
        conn.commit()
    with app.test_client() as client:
        yield client

def test_open_rappi_restaurant(client):
    response = client.post('/api/open-rappi', data={"store_id": "111", "target_type": "store"})
    assert response.status_code == 302
    assert response.location == "https://www.rappi.com.mx/restaurantes/111"

def test_open_rappi_market(client):
    # NOTE: product_exact is UNSUPPORTED because Rappi Web UI lacks stable product IDs routes.
    # So we ALWAYS fallback to store exact landing.
    response = client.post('/api/open-rappi', data={"store_id": "222", "target_type": "store"})
    assert response.status_code == 302
    assert response.location == "https://www.rappi.com.mx/tiendas/222"

def test_open_rappi_rejects_untrusted_target(client):
    response = client.post('/api/open-rappi', data={"target_type": "store"})
    assert response.status_code == 302
    assert response.location == "/" # redirects home

def test_open_rappi_product_unsupported_fallback(client):
    response = client.post('/api/open-rappi', data={"store_id": "111", "target_type": "product"})
    assert response.status_code == 302
    assert response.location == "https://www.rappi.com.mx/restaurantes/111"
