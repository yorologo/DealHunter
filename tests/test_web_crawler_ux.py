import pytest
import sqlite3
from flask import url_for
from dealhunter.web.app import create_app
from werkzeug.exceptions import BadRequest

@pytest.fixture
def app_and_db(tmp_path):
    db_path = str(tmp_path / 'test.db')
    from dealhunter.db import setup_db
    setup_db(db_path)
    
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'dev'
    })
    
    yield app, db_path

@pytest.fixture
def client(app_and_db):
    app, _ = app_and_db
    return app.test_client()

def test_web_start_creates_exactly_one_run(client, app_and_db, monkeypatch):
    app, db_path = app_and_db
    
    import subprocess
    monkeypatch.setattr("dealhunter.config.load_config", lambda: {"location": {"lat": 19.4326, "lng": -99.1332}})
    popen_calls = []
    monkeypatch.setattr("dealhunter.config.load_config", lambda: {"location": {"lat": 19.4326, "lng": -99.1332}})
    class MockPopen:
        def __init__(self, *args, **kwargs):
            popen_calls.append((args, kwargs))
    
    monkeypatch.setattr(subprocess, "Popen", MockPopen)
    
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['csrf_token'] = 'token'
        
        # Test HTMX redirect
        response = c.post('/admin/runs/start', headers={'X-CSRF-Token': 'token', 'HX-Request': 'true'})
        print('BODY:', response.get_data(as_text=True)); assert response.status_code == 200
        assert 'HX-Redirect' in response.headers
        
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT run_id FROM runs")
        runs = cur.fetchall()
        assert len(runs) == 1
        
        run_id = runs[0][0]
        assert len(popen_calls) == 1
        assert run_id in popen_calls[0][0][0]

def test_run_start_normal_post_redirect(client, app_and_db, monkeypatch):
    app, db_path = app_and_db
    
    import subprocess
    monkeypatch.setattr("dealhunter.config.load_config", lambda: {"location": {"lat": 19.4326, "lng": -99.1332}})
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: None)
    
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['csrf_token'] = 'token'
            
        # Test normal redirect
        response = c.post('/admin/runs/start', headers={'X-CSRF-Token': 'token'})
        print('BODY:', response.get_data(as_text=True)); assert response.status_code == 302
        assert '/admin/runs/run_' in response.headers['Location']

def test_csrf_error_gets_human_page(client, app_and_db):
    app, _ = app_and_db
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['csrf_token'] = 'token'
            
        # Invalid CSRF token
        response = c.post('/admin/catalog-sync/session/store', data={'csrf_token': 'wrong'})
        assert response.status_code == 400
        assert b"Tu sesi" in response.data or b"CSRF" in response.data

def test_generic_400_is_not_labeled_csrf(app_and_db):
    app, _ = app_and_db
    
    @app.route('/test-400')
    def test_400():
        raise BadRequest("This is a generic bad request")
        
    with app.test_client() as c:
        response = c.get('/test-400')
        assert response.status_code == 400
        assert b"CSRF" not in response.data
        assert b"generic bad request" in response.data

def test_run_start_missing_location(client, app_and_db, monkeypatch):
    app, db_path = app_and_db
    monkeypatch.setattr("dealhunter.config.load_config", lambda: {})
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['csrf_token'] = 'token'
        response = c.post('/admin/runs/start', headers={'X-CSRF-Token': 'token'})
        assert response.status_code == 400
        body = response.get_data(as_text=True)
        assert "Ubicación (lat/lng) no configurada" in body

def test_run_start_valid_location(client, app_and_db, monkeypatch):
    app, db_path = app_and_db
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: None)
    monkeypatch.setattr("dealhunter.config.load_config", lambda: {"location": {"lat": 19.43, "lng": -99.13}})
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['csrf_token'] = 'token'
        response = c.post('/admin/runs/start', headers={'X-CSRF-Token': 'token'})
        assert response.status_code == 302
