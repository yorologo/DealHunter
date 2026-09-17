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
    monkeypatch.setattr("dealhunter.web.admin.get_merged_config", lambda *_args, **_kwargs: {"lat": 19.4326, "lng": -99.1332, "radius": 5.0})
    popen_calls = []
    monkeypatch.setattr("dealhunter.web.admin.get_merged_config", lambda *_args, **_kwargs: {"lat": 19.4326, "lng": -99.1332, "radius": 5.0})
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
    monkeypatch.setattr("dealhunter.web.admin.get_merged_config", lambda *_args, **_kwargs: {"lat": 19.4326, "lng": -99.1332, "radius": 5.0})
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
    monkeypatch.setattr("dealhunter.web.admin.get_merged_config", lambda *_args, **_kwargs: {"lat": 19.43, "lng": -99.13, "radius": 5.0})
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['csrf_token'] = 'token'
        response = c.post('/admin/runs/start', headers={'X-CSRF-Token': 'token'})
        assert response.status_code == 302


def test_run_start_requires_csrf(app_and_db, monkeypatch):
    app, _ = app_and_db
    monkeypatch.setattr(
        "dealhunter.web.admin.get_merged_config",
        lambda *_a, **_k: {"lat": 19.43, "lng": -99.13, "radius": 5.0},
    )
    with app.test_client() as c:
        assert c.post("/admin/runs/start").status_code == 400


def test_run_start_rejects_second_and_spawns_once(app_and_db, monkeypatch):
    app, db_path = app_and_db
    import subprocess

    monkeypatch.setattr(
        "dealhunter.web.admin.get_merged_config",
        lambda *_a, **_k: {"lat": 19.43, "lng": -99.13, "radius": 5.0},
    )
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append((a, k)))

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["csrf_token"] = "token"
        first = c.post("/admin/runs/start", data={"csrf_token": "token"})
        second = c.post("/admin/runs/start", data={"csrf_token": "token"})

    assert first.status_code == 302
    assert second.status_code == 400
    assert len(calls) == 1
    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM runs WHERE status='RUNNING'"
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_popen_failure_marks_reserved_run_failed(app_and_db, monkeypatch):
    app, db_path = app_and_db
    import subprocess

    monkeypatch.setattr(
        "dealhunter.web.admin.get_merged_config",
        lambda *_a, **_k: {"lat": 19.43, "lng": -99.13, "radius": 5.0},
    )

    def fail_popen(*_a, **_k):
        raise OSError("simulated spawn failure")

    monkeypatch.setattr(subprocess, "Popen", fail_popen)

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["csrf_token"] = "token"
        response = c.post("/admin/runs/start", data={"csrf_token": "token"})

    assert response.status_code == 500
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT status, finished_at, run_metadata FROM runs"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "FAILED"
    assert row[1] is not None
    assert '"phase":"FAILED"' in row[2]


def _insert_progress_run(db_path, run_id, status, progress, started_at="2026-09-17 12:00:00"):
    import json

    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO runs
           (run_id, started_at, status, crawler_mode, run_metadata)
           VALUES (?, ?, ?, 'ZONE_INVENTORY', ?)""",
        (run_id, started_at, status, json.dumps({"progress": progress})),
    )
    conn.commit()
    conn.close()


def test_progress_query_real_percentage_and_running_cap(app_and_db):
    from dealhunter.web.admin_queries import get_run_progress

    _, db_path = app_and_db
    base = {
        "phase": "CRAWLING",
        "completed": 2,
        "total": 4,
        "unit": "tiendas",
        "updated_at": "2026-09-17T12:00:10Z",
        "phase_started_at": "2026-09-17T12:00:00Z",
    }
    _insert_progress_run(db_path, "p50", "RUNNING", base)
    _insert_progress_run(db_path, "p99", "RUNNING", {**base, "completed": 4})
    _insert_progress_run(db_path, "p100", "SUCCESS", {**base, "completed": 4})

    assert get_run_progress(db_path, "p50")["percentage"] == 50
    assert get_run_progress(db_path, "p99")["percentage"] == 99
    assert get_run_progress(db_path, "p100")["percentage"] == 100


def test_indeterminate_progress_for_starting_discovery_and_search(app_and_db):
    from dealhunter.web.admin_queries import get_run_progress

    _, db_path = app_and_db
    for run_id, phase, completed in (
        ("start", "STARTING", 0),
        ("discover", "DISCOVERING", 0),
        ("search", "SEARCHING", 12),
    ):
        _insert_progress_run(
            db_path,
            run_id,
            "RUNNING",
            {
                "phase": phase,
                "completed": completed,
                "total": None,
                "unit": "consultas" if phase == "SEARCHING" else None,
                "updated_at": "2026-09-17T12:00:10Z",
                "phase_started_at": "2026-09-17T12:00:00Z",
            },
        )
        progress = get_run_progress(db_path, run_id)
        assert progress["percentage"] is None
        assert progress["total"] is None


def test_eta_requires_real_sample_then_appears(app_and_db):
    from datetime import datetime, timezone
    from dealhunter.web.admin_queries import get_run_progress

    _, db_path = app_and_db
    phase_start = "2026-09-17T12:00:00Z"
    common = {
        "phase": "CRAWLING",
        "total": 6,
        "unit": "tiendas",
        "updated_at": "2026-09-17T12:01:00Z",
        "phase_started_at": phase_start,
    }
    _insert_progress_run(db_path, "eta-none", "RUNNING", {**common, "completed": 1})
    _insert_progress_run(db_path, "eta-real", "RUNNING", {**common, "completed": 2})
    now = datetime(2026, 9, 17, 12, 1, 0, tzinfo=timezone.utc)

    assert get_run_progress(db_path, "eta-none", now=now)["eta_minutes"] is None
    eta = get_run_progress(db_path, "eta-real", now=now)["eta_minutes"]
    assert eta == 2


def test_progress_endpoint_is_local_read_only(app_and_db, monkeypatch):
    app, db_path = app_and_db
    _insert_progress_run(
        db_path,
        "local-only",
        "RUNNING",
        {
            "phase": "CRAWLING",
            "completed": 1,
            "total": 4,
            "unit": "tiendas",
            "updated_at": "2026-09-17T12:00:10Z",
            "phase_started_at": "2026-09-17T12:00:00Z",
        },
    )
    before = sqlite3.connect(db_path).execute(
        "SELECT status, run_metadata FROM runs WHERE run_id='local-only'"
    ).fetchone()

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("progress GET used network")),
    )
    with app.test_client() as c:
        response = c.get("/admin/runs/local-only/progress")

    after_conn = sqlite3.connect(db_path)
    after = after_conn.execute(
        "SELECT status, run_metadata FROM runs WHERE run_id='local-only'"
    ).fetchone()
    after_conn.close()
    assert response.status_code == 200
    assert before == after
    assert b"25%" in response.data


@pytest.mark.parametrize("status", ["SUCCESS", "PARTIAL", "FAILED"])
def test_terminal_progress_unlocks_with_single_refresh(app_and_db, status):
    app, db_path = app_and_db
    _insert_progress_run(
        db_path,
        f"terminal-{status}",
        status,
        {
            "phase": "FINALIZING",
            "completed": 4,
            "total": 4,
            "unit": "tiendas",
            "updated_at": "2026-09-17T12:00:10Z",
            "phase_started_at": "2026-09-17T12:00:00Z",
        },
    )
    with app.test_client() as c:
        response = c.get(f"/admin/runs/terminal-{status}/progress")
    assert response.status_code == 200
    assert response.headers["HX-Refresh"] == "true"


def test_refresh_reconstructs_blocking_modal_from_sqlite(app_and_db):
    app, db_path = app_and_db
    _insert_progress_run(
        db_path,
        "refresh-run",
        "RUNNING",
        {
            "phase": "CRAWLING",
            "completed": 2,
            "total": 4,
            "unit": "tiendas",
            "updated_at": "2026-09-17T12:00:10Z",
            "phase_started_at": "2026-09-17T12:00:00Z",
        },
    )
    with app.test_client() as c:
        response = c.get("/admin/runs/refresh-run")
    assert response.status_code == 200
    assert b'id="run-progress-overlay"' in response.data
    assert b"/admin/runs/refresh-run/progress" in response.data
    assert b"50%" in response.data
    assert b"El crawler continuar" in response.data
    assert b'hx-get="/admin/runs/refresh-run"' not in response.data


def test_runs_page_uses_normal_post_and_htmx_asset_is_available(app_and_db, monkeypatch):
    app, _ = app_and_db
    monkeypatch.setattr(
        "dealhunter.web.admin.get_merged_config",
        lambda *_a, **_k: {"lat": 19.43, "lng": -99.13, "radius": 5.0},
    )
    with app.test_client() as c:
        page = c.get("/admin/runs")
        asset = c.get("/static/js/htmx.min.js")
    assert page.status_code == 200
    assert asset.status_code == 200
    assert b'action="/admin/runs/start"' in page.data
    assert b'hx-post="/admin/runs/start"' not in page.data
    assert b"Iniciando..." not in page.data
    assert b"Iniciar crawler Rappi" in page.data
    assert b"Ubicaci" in page.data and b"Configurada" in page.data


def test_runs_page_uses_lifecycle_active_window(app_and_db):
    app, db_path = app_and_db
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO runs (run_id, started_at, status)
           VALUES ('stale-running', datetime('now', '-3 hours'), 'RUNNING')"""
    )
    conn.commit()
    conn.close()

    with app.test_client() as c:
        page = c.get("/admin/runs")
    assert page.status_code == 200
    assert b"Ya hay un crawler ejecut" not in page.data
    assert b"disabled title=" not in page.data


def test_runs_missing_location_shows_preflight_without_post_or_process(app_and_db, monkeypatch):
    app, db_path = app_and_db
    import subprocess

    monkeypatch.setattr(
        "dealhunter.web.admin.get_merged_config",
        lambda *_a, **_k: {"lat": None, "lng": None, "radius": 5.0},
    )
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append((a, k)))

    with app.test_client() as c:
        page = c.get("/admin/runs")

    assert page.status_code == 200
    assert b'id="missingLocationModal"' in page.data
    assert b'/admin/settings?return_to=/admin/runs#location' in page.data
    assert b'action="/admin/runs/start"' not in page.data
    assert calls == []
    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    finally:
        conn.close()


def test_direct_start_without_location_still_rejected_without_run_or_process(app_and_db, monkeypatch):
    app, db_path = app_and_db
    import subprocess

    monkeypatch.setattr(
        "dealhunter.web.admin.get_merged_config",
        lambda *_a, **_k: {"lat": None, "lng": None, "radius": 5.0},
    )
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append((a, k)))

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["csrf_token"] = "token"
        rv = c.post("/admin/runs/start", data={"csrf_token": "token"})

    assert rv.status_code == 400
    assert calls == []
    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    finally:
        conn.close()


def test_location_save_return_to_runs_does_not_autostart_crawler(app_and_db, monkeypatch):
    app, db_path = app_and_db
    import subprocess

    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["csrf_token"] = "token"
        rv = c.post(
            "/admin/settings/location",
            data={
                "csrf_token": "token",
                "lat": "20.5",
                "lng": "-103.4",
                "return_to": "/admin/runs",
            },
        )

    assert rv.status_code == 302
    assert rv.headers["Location"] == "/admin/runs"
    assert calls == []
    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    finally:
        conn.close()


def test_runs_get_is_local_only_with_preflight(app_and_db, monkeypatch):
    app, _ = app_and_db
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("GET runs used network")),
    )
    monkeypatch.setattr(
        "dealhunter.web.admin.get_merged_config",
        lambda *_a, **_k: {"lat": None, "lng": None, "radius": 5.0},
    )
    with app.test_client() as c:
        rv = c.get("/admin/runs")
    assert rv.status_code == 200
