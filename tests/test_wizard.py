import pytest
import os
from unittest.mock import patch, MagicMock
from dealhunter.web.app import create_app
from dealhunter.secret_store import SessionService

@pytest.fixture
def client(tmp_path):
    os.environ['HOME'] = str(tmp_path)
    os.environ['XDG_CONFIG_HOME'] = str(tmp_path / ".config")
    app = create_app(test_config={'TESTING': True, 'DATABASE': ':memory:'})
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['csrf_token'] = 'test_token'
        yield client

def test_wizard_route(client):
    response = client.get('/admin/catalog-sync/wizard')
    assert response.status_code == 200
    assert b'ASISTENTE DE SESI' in response.data
    # Helper copy present
    assert b'Copiar herramienta' in response.data
    assert b'javascript:(function' in response.data
    
    # Obsolete instruction absent
    assert b"localStorage.getItem('access_token')" not in response.data
    # JWT placeholder absent
    assert b"eyJhbGci" not in response.data

@patch('dealhunter.secret_store.SessionService')
def test_wizard_post(mock_session_service_class, client):
    mock_svc = MagicMock()
    mock_session_service_class.return_value = mock_svc
    mock_svc.store_persistent.return_value = True
    
    response = client.post('/admin/catalog-sync/wizard/store', data={
        'csrf_token': 'test_token',
        'token': 'Bearer ft.gAAAA1234',
        'session_mode': 'persistent',
        'return_path': '/admin/catalog-sync'
    })
    
    assert response.status_code == 302
    assert response.headers['Location'] == '/admin/catalog-sync'
    mock_svc.store_persistent.assert_called_with('Bearer ft.gAAAA1234')

def test_token_never_rerendered(client, tmp_path):
    svc = SessionService(str(tmp_path / "test_session.enc"))
    svc.store_persistent("my_super_secret_token_ft_gAAAA")
    
    response = client.get('/admin/catalog-sync/wizard')
    assert b"my_super_secret_token_ft_gAAAA" not in response.data

def test_csrf_required(client):
    response = client.post('/admin/catalog-sync/wizard/store', data={'token': 'abc'})
    assert response.status_code == 400
