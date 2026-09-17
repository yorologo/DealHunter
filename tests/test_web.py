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
    
    # Setup dummy db
    conn = setup_db(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s1', 'Soriana', '', 'market')")
    c.execute("INSERT INTO products (product_id, store_id, name) VALUES ('p1', 's1', 'Coca Cola 2 L')")
    c.execute("INSERT INTO runs (run_id, started_at) VALUES ('run1', '2026-08-19')")
    # Need at least 3 obs for NEW_LOW or REAL_DEAL, but let's leave it mostly empty
    # to test empty states gracefully.
    conn.commit()
    conn.close()
    
    app = create_app({'DATABASE': db_path, 'TESTING': True})
    yield app
    os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_home(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'DealHunter' in rv.data
    assert b'Todav\xc3\xada no hay REAL DEAL' in rv.data # Empty state message

def test_search(client):
    rv = client.get('/search?q=Coca')
    assert rv.status_code == 200
    assert b'Coca Cola' in rv.data
    
def test_search_hx(client):
    rv = client.get('/search?q=Coca', headers={'HX-Request': 'true'})
    assert rv.status_code == 200
    assert b'list-group-item' in rv.data

def test_watchlist_page(client, app):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute("INSERT INTO watchlist (query, target_price, enabled) VALUES ('Coca Cola', 35.0, 1)")
        conn.commit()
    rv = client.get('/watchlist')
    assert rv.status_code == 200
    assert b'Coca Cola' in rv.data
    assert b'$35.00' in rv.data
    assert b'/search?q=Coca+Cola' in rv.data or b'/search?q=Coca%20Cola' in rv.data

def test_alerts_placeholder(client):
    rv = client.get('/alerts')
    assert rv.status_code == 200
    assert b'Pr\xc3\xb3ximamente' in rv.data or b'read-only' in rv.data

def test_404(client):
    rv = client.get('/not-exists')
    assert rv.status_code == 404
    assert b'No Encontrado' in rv.data

def test_cli_help():
    import subprocess
    res = subprocess.run("python3 bin/rappi-historico web --help", shell=True, capture_output=True, text=True)
    assert "web" in res.stdout
    assert "--port" in res.stdout

def test_run_server_initializes_fresh_database(tmp_path, monkeypatch):
    import dealhunter.web.app as webapp

    db_path = tmp_path / "fresh-web.db"
    monkeypatch.setattr(webapp, "get_default_db_path", lambda: str(db_path))
    monkeypatch.setattr(webapp, "_production_secret_key", lambda: "test-only-secret")
    monkeypatch.setattr(webapp, "is_termux", lambda: False)
    monkeypatch.setattr(webapp.Flask, "run", lambda self, **kwargs: None)

    webapp.run_server(port=18765)

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == 17
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='alerts'").fetchone()[0] == 1

