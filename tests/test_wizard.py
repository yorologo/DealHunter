import pytest
from dealhunter.web.app import create_app

@pytest.fixture
def client():
    app = create_app(test_config={'TESTING': True, 'DATABASE': ':memory:'})
    with app.test_client() as client:
        yield client

def test_wizard_route(client):
    response = client.get('/admin/catalog-sync/wizard')
    assert response.status_code == 200
    assert b'Asistente de Import' in response.data
