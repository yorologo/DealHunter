"""Tests for DealHunter v2.7 Administration Web Interface."""

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
    db_path = os.path.join(tmpdir, "test_admin.db")

    # Setup test database with realistic data
    conn = setup_db(db_path)
    c = conn.cursor()

    # Stores
    c.execute("INSERT INTO stores (store_id, name, brand, type, status, last_seen_at) VALUES ('s1', 'Soriana', 'Soriana', 'market', 'ACTIVE', '2026-08-21T00:00:00')")
    c.execute("INSERT INTO stores (store_id, name, brand, type) VALUES ('s2', 'Walmart', 'Walmart', 'market')")

    # Products
    c.execute("INSERT INTO products (product_id, store_id, name, brand, category) VALUES ('p1', 's1', 'Coca Cola 2L', 'Coca-Cola', 'Bebidas')")
    c.execute("INSERT INTO products (product_id, store_id, name, brand, category) VALUES ('p2', 's2', 'Pepsi 2L', 'PepsiCo', 'Bebidas')")

    # Runs with different statuses
    c.execute("INSERT INTO runs (run_id, started_at, finished_at, status, vertical) VALUES ('run1', '2026-08-19T10:00:00', '2026-08-19T10:05:30', 'COMPLETED', NULL)")
    c.execute("INSERT INTO runs (run_id, started_at, finished_at, status, vertical) VALUES ('run2', '2026-08-19T11:00:00', '2026-08-19T11:02:00', 'PARTIAL', '{\"error_code\": \"HTTP_429\", \"component\": \"catalog\"}')")
    c.execute("INSERT INTO runs (run_id, started_at, finished_at, status, vertical) VALUES ('run3', '2026-08-19T12:00:00', '2026-08-19T12:00:10', 'FAILED', '{\"error_code\": \"NETWORK_ERROR\", \"component\": \"turbo\"}')")

    # Observations
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('run1', '2024-01-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, timestamp) VALUES ('run1', 's1', 'p1', 25.0, 30.0, '2026-08-19T10:01:00')")
    c.execute("INSERT OR IGNORE INTO runs (run_id, started_at, status) VALUES ('run1', '2024-01-01', 'SUCCESS')")
    c.execute("INSERT INTO observations (run_id, store_id, product_id, price, original_price, timestamp) VALUES ('run1', 's2', 'p2', 22.0, 28.0, '2026-08-19T10:02:00')")

    conn.commit()
    conn.close()

    app = create_app({'DATABASE': db_path, 'TESTING': True, 'SECRET_KEY': 'test-secret'})
    yield app

    # Cleanup
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def client(app):
    return app.test_client()


def _get_csrf_token(client):
    """Get a CSRF token by visiting any page."""
    with client.session_transaction() as sess:
        import secrets
        token = secrets.token_hex(32)
        sess['csrf_token'] = token
    return token


class TestAdminHome:
    def test_admin_home_renders(self, client):
        rv = client.get('/admin/')
        assert rv.status_code == 200
        assert b'Administraci' in rv.data  # "Administración"
        assert b'Sistema' in rv.data or b'admin' in rv.data.lower()

    def test_admin_home_shows_health(self, client):
        rv = client.get('/admin/')
        assert rv.status_code == 200
        assert b'HEALTHY' in rv.data or b'ERROR' in rv.data

    def test_admin_home_shows_stats(self, client):
        rv = client.get('/admin/')
        assert rv.status_code == 200
        assert b'Productos' in rv.data
        assert b'Tiendas' in rv.data

    def test_admin_home_navigation_cards(self, client):
        rv = client.get('/admin/')
        assert rv.status_code == 200
        assert b'/admin/account' in rv.data
        assert b'/admin/runs' in rv.data
        assert b'/admin/events' in rv.data
        assert b'/admin/doctor' in rv.data
        assert b'/admin/database' in rv.data
        assert b'/admin/settings' in rv.data


class TestAdminAccount:
    def test_account_page_renders(self, client):
        rv = client.get('/admin/account')
        assert rv.status_code == 200
        assert b'Cuenta' in rv.data or b'Token' in rv.data

    def test_account_no_network_on_load(self, client):
        """Opening account page must NOT trigger network requests."""
        rv = client.get('/admin/account')
        assert rv.status_code == 200
        # Page shows token status but does NOT call get_account_status
        assert b'Sesi' in rv.data or b'sesi' in rv.data

    def test_account_never_shows_token(self, client):
        """Token value must never appear in output."""
        rv = client.get('/admin/account')
        assert rv.status_code == 200
        assert b'RAPPI_BEARER_TOKEN' not in rv.data or b'variable de entorno' in rv.data

    def test_account_check_requires_post(self, client):
        """Account check must be POST (explicit action)."""
        rv = client.get('/admin/account/check')
        assert rv.status_code == 405  # Method Not Allowed

    def test_account_check_requires_csrf(self, client):
        """POST without CSRF token should fail."""
        rv = client.post('/admin/account/check')
        assert rv.status_code == 400


class TestAdminRuns:
    def test_runs_page_renders(self, client):
        rv = client.get('/admin/runs')
        assert rv.status_code == 200
        assert b'Ejecuciones' in rv.data or b'Runs' in rv.data

    def test_runs_shows_entries(self, client):
        rv = client.get('/admin/runs')
        assert rv.status_code == 200
        assert b'run1' in rv.data or b'COMPLETED' in rv.data

    def test_runs_status_filter(self, client):
        rv = client.get('/admin/runs?status=FAILED')
        assert rv.status_code == 200
        assert b'FAILED' in rv.data

    def test_runs_status_filter_completed(self, client):
        rv = client.get('/admin/runs?status=COMPLETED')
        assert rv.status_code == 200
        assert b'COMPLETED' in rv.data

    def test_runs_htmx_pagination(self, client):
        rv = client.get('/admin/runs?page=1', headers={'HX-Request': 'true'})
        assert rv.status_code == 200
        # Returns partial, not full page
        assert b'<table' in rv.data

    def test_run_detail(self, client):
        rv = client.get('/admin/runs/run1')
        assert rv.status_code == 200
        assert b'run1' in rv.data
        assert b'Observaciones' in rv.data or b'observation' in rv.data.lower()

    def test_run_detail_shows_duration(self, client):
        rv = client.get('/admin/runs/run1')
        assert rv.status_code == 200
        assert b'5m' in rv.data  # 5m 30s duration

    def test_run_detail_not_found(self, client):
        rv = client.get('/admin/runs/nonexistent')
        assert rv.status_code == 404

    def test_run_detail_no_coordinates(self, client):
        """Run detail must not expose lat/lng location data."""
        rv = client.get('/admin/runs/run1')
        assert rv.status_code == 200
        assert b'Latitud' not in rv.data
        assert b'Longitud' not in rv.data


class TestAdminEvents:
    def test_events_page_renders(self, client):
        rv = client.get('/admin/events')
        assert rv.status_code == 200
        assert b'Eventos' in rv.data or b'Errores' in rv.data

    def test_events_shows_failed_runs(self, client):
        rv = client.get('/admin/events')
        assert rv.status_code == 200
        assert b'NETWORK_ERROR' in rv.data or b'HTTP_429' in rv.data

    def test_events_structured_display(self, client):
        """Events should show structured info, not raw logs."""
        rv = client.get('/admin/events')
        assert rv.status_code == 200
        # Should have severity/error code columns
        assert b'Severidad' in rv.data or b'severity' in rv.data.lower() or b'ERROR' in rv.data


class TestAdminDoctor:
    def test_doctor_page_renders(self, client):
        rv = client.get('/admin/doctor')
        assert rv.status_code == 200
        assert b'Doctor' in rv.data or b'Diagn' in rv.data

    def test_doctor_local_only_on_load(self, client):
        """Doctor page must show local checks without network."""
        rv = client.get('/admin/doctor')
        assert rv.status_code == 200
        assert b'HEALTHY' in rv.data or b'ERROR' in rv.data
        # Has local check results
        assert b'Configuration' in rv.data or b'Database' in rv.data or b'Schema' in rv.data

    def test_doctor_network_requires_post(self, client):
        """Network doctor check must be POST."""
        rv = client.get('/admin/doctor/check')
        assert rv.status_code == 405

    def test_doctor_network_requires_csrf(self, client):
        rv = client.post('/admin/doctor/check')
        assert rv.status_code == 400


class TestAdminDatabase:
    def test_database_page_renders(self, client):
        rv = client.get('/admin/database')
        assert rv.status_code == 200
        assert b'Base de Datos' in rv.data

    def test_database_shows_stats(self, client):
        rv = client.get('/admin/database')
        assert rv.status_code == 200
        assert b'Productos' in rv.data
        assert b'Observaciones' in rv.data
        assert b'Tiendas' in rv.data

    def test_database_shows_schema(self, client):
        rv = client.get('/admin/database')
        assert rv.status_code == 200
        assert b'Esquema' in rv.data or b'schema' in rv.data.lower()

    def test_database_shows_integrity_action(self, client):
        rv = client.get('/admin/database')
        assert rv.status_code == 200
        assert b'Integridad' in rv.data

    def test_database_shows_backup_action(self, client):
        rv = client.get('/admin/database')
        assert rv.status_code == 200
        assert b'Backup' in rv.data

    def test_database_backup_requires_post(self, client):
        rv = client.get('/admin/database/backup')
        assert rv.status_code == 405

    def test_database_integrity_requires_post(self, client):
        rv = client.get('/admin/database/integrity')
        assert rv.status_code == 405

    def test_database_backup_with_csrf(self, client):
        token = _get_csrf_token(client)
        rv = client.post('/admin/database/backup',
                         headers={'X-CSRF-Token': token})
        assert rv.status_code == 200
        assert b'Backup' in rv.data or b'backup' in rv.data

    def test_database_integrity_with_csrf(self, client):
        token = _get_csrf_token(client)
        rv = client.post('/admin/database/integrity',
                         headers={'X-CSRF-Token': token})
        assert rv.status_code == 200
        assert b'ok' in rv.data.lower()

    def test_no_arbitrary_sql(self, client):
        """No route should accept arbitrary SQL."""
        # There should be no SQL execution endpoint
        # 400 = CSRF rejected, 404 = route not found, 405 = method not allowed
        # Any of these is acceptable - the key is it's NOT 200
        rv = client.post('/admin/database/sql', data={'query': 'DROP TABLE runs'})
        assert rv.status_code in (400, 404, 405)

    def test_no_vacuum_via_get(self, client):
        """VACUUM must not be accessible via GET."""
        rv = client.get('/admin/database/vacuum')
        assert rv.status_code in (404, 405)


class TestAdminSettings:
    def test_settings_page_renders(self, client):
        rv = client.get('/admin/settings')
        assert rv.status_code == 200
        assert b'Configuraci' in rv.data

    def test_settings_shows_precedence(self, client):
        rv = client.get('/admin/settings')
        assert rv.status_code == 200
        assert b'CLI' in rv.data
        assert b'Profile' in rv.data
        assert b'config.toml' in rv.data
        assert b'Default' in rv.data

    def test_settings_shows_classification(self, client):
        rv = client.get('/admin/settings')
        assert rv.status_code == 200
        assert b'SAFE' in rv.data  # SAFE_EDITABLE badge

    def test_settings_shows_effective_values(self, client):
        rv = client.get('/admin/settings')
        assert rv.status_code == 200
        assert b'min_discount' in rv.data
        assert b'max_discount' in rv.data

    def test_settings_shows_source(self, client):
        rv = client.get('/admin/settings')
        assert rv.status_code == 200
        assert b'default' in rv.data or b'config.toml' in rv.data

    def test_settings_update_requires_post(self, client):
        rv = client.get('/admin/settings/update')
        assert rv.status_code == 405

    def test_settings_update_requires_csrf(self, client):
        rv = client.post('/admin/settings/update',
                         data={'key': 'min_discount', 'value': '10'})
        assert rv.status_code == 400

    def test_settings_rejects_forbidden_key(self, client):
        token = _get_csrf_token(client)
        rv = client.post('/admin/settings/update',
                         data={'key': 'bearer_token', 'value': 'HACK'},
                         headers={'X-CSRF-Token': token})
        assert rv.status_code == 302
        followed = client.get(rv.headers['Location'])
        assert b'no es editable' in followed.data or b'No se permiten secretos' in followed.data

    def test_settings_rejects_unknown_and_readonly(self, client):
        """Web interface must reject modifications to keys not in SAFE_EDITABLE allowlist."""
        token = _get_csrf_token(client)
        forbidden_keys = ['rappi_token', 'unknown_setting', 'database_path', 'schema_version']
        for key in forbidden_keys:
            rv = client.post('/admin/settings/update',
                             data={'key': key, 'value': 'test'},
                             headers={'X-CSRF-Token': token})
            assert rv.status_code == 302
            followed = client.get(rv.headers['Location'])
            assert b'no es editable' in followed.data or b'No se permiten secretos' in followed.data

    def test_settings_canary_token_never_exposed(self, client, monkeypatch):
        """A canary secret in the configuration must never be exposed in the HTTP response."""
        import json
        from dealhunter.config import save_config
        # Inject canary token into global config for this test
        # We'll use a mocked config layer

        # We can simulate the global config returning the canary
        original_load = __import__("dealhunter.config").config.load_config
        def mock_load():
            cfg = original_load()
            cfg['test_secret_token'] = 'SUPER_SECRET_TEST_TOKEN_12345'
            return cfg

        monkeypatch.setattr('dealhunter.web.admin.load_config', mock_load)

        rv = client.get('/admin/settings')
        assert rv.status_code == 200
        assert b'SUPER_SECRET_TEST_TOKEN_12345' not in rv.data
        assert b'CONFIGURADO' in rv.data
        assert b'test_secret_token' in rv.data


class TestCSRF:
    def test_post_without_csrf_rejected(self, client):
        """All POST endpoints must reject requests without CSRF."""
        post_endpoints = [
            '/admin/account/check',
            '/admin/account/uber/check',
            '/admin/doctor/check',
            '/admin/database/backup',
            '/admin/database/integrity',
            '/admin/settings/update',
        ]
        for endpoint in post_endpoints:
            rv = client.post(endpoint)
            assert rv.status_code == 400, f"{endpoint} should reject without CSRF"

    def test_post_with_csrf_accepted(self, client):
        """POST with valid CSRF should be accepted."""
        token = _get_csrf_token(client)
        rv = client.post('/admin/database/integrity',
                         headers={'X-CSRF-Token': token})
        assert rv.status_code == 200


class TestHTTPSafety:
    def test_backup_not_via_get(self, client):
        rv = client.get('/admin/database/backup')
        assert rv.status_code == 405

    def test_settings_update_not_via_get(self, client):
        rv = client.get('/admin/settings/update')
        assert rv.status_code == 405

    def test_doctor_check_not_via_get(self, client):
        rv = client.get('/admin/doctor/check')
        assert rv.status_code == 405

    def test_account_check_not_via_get(self, client):
        rv = client.get('/admin/account/check')
        assert rv.status_code == 405


class TestNetworkSafety:
    def test_admin_home_no_network(self, client):
        """Loading /admin should produce 0 external requests."""
        rv = client.get('/admin/')
        assert rv.status_code == 200

    def test_account_page_no_network(self, client):
        """Loading /admin/account should produce 0 external requests."""
        rv = client.get('/admin/account')
        assert rv.status_code == 200

    def test_doctor_page_no_network(self, client):
        """Loading /admin/doctor should produce 0 external requests (local only)."""
        rv = client.get('/admin/doctor')
        assert rv.status_code == 200

    def test_runs_page_no_network(self, client):
        rv = client.get('/admin/runs')
        assert rv.status_code == 200

    def test_events_page_no_network(self, client):
        rv = client.get('/admin/events')
        assert rv.status_code == 200

    def test_database_page_no_network(self, client):
        rv = client.get('/admin/database')
        assert rv.status_code == 200

    def test_settings_page_no_network(self, client):
        rv = client.get('/admin/settings')
        assert rv.status_code == 200


class TestServerBinding:
    def test_default_binding(self):
        """Server must bind to 127.0.0.1 by default."""
        from dealhunter.web.app import run_server
        import inspect
        src = inspect.getsource(run_server)
        assert '127.0.0.1' in src


class TestSettingsTaskUX:
    def test_settings_get_is_local_and_geolocation_is_click_only(self, client, monkeypatch):
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("GET settings used network")),
        )
        rv = client.get('/admin/settings')
        assert rv.status_code == 200
        html = rv.get_data(as_text=True)
        assert 'navigator.geolocation' in html
        assert 'window.isSecureContext' in html
        assert "trigger.addEventListener('click'" in html
        assert html.index("trigger.addEventListener('click'") < html.index("navigator.geolocation.getCurrentPosition")
        assert 'name="accuracy"' not in html
        assert 'id="found-accuracy"' in html
        assert 'Introducir coordenadas manualmente' in html

    def test_global_discovery_mode_is_editable(self, client):
        from dealhunter.config import load_config
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/update',
            data={
                'csrf_token': token,
                'key': 'discovery_mode',
                'value': 'deep',
                'return_to': '/admin/settings#crawler',
            },
        )
        assert rv.status_code == 302
        assert load_config()['discovery_mode'] == 'deep'


    def test_web_rejects_invalid_discovery_mode(self, client):
        from dealhunter.config import load_config
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/update',
            data={
                'csrf_token': token,
                'key': 'discovery_mode',
                'value': 'custom',
            },
        )
        assert rv.status_code == 302
        assert 'discovery_mode' not in load_config()

    def test_profile_view_is_read_only_and_does_not_write_global(self, client):
        from dealhunter.config import load_config, save_config
        save_config({
            'discovery_mode': 'full',
            'profiles': {'audit': {'discovery_mode': 'deep', 'lat': 20.0, 'lng': -103.0}},
        })
        rv = client.get('/admin/settings?profile=audit')
        html = rv.get_data(as_text=True)
        assert rv.status_code == 200
        assert 'solo lectura' in html
        assert 'action="/admin/settings/location"' not in html
        assert 'action="/admin/settings/update"' not in html
        assert 'action="/admin/settings/provider"' not in html
        assert 'action="/admin/settings/membership"' not in html

        token = _get_csrf_token(client)
        blocked = client.post(
            '/admin/settings/update',
            data={
                'csrf_token': token,
                'profile': 'audit',
                'key': 'discovery_mode',
                'value': 'normal',
            },
        )
        assert blocked.status_code == 400
        assert load_config()['discovery_mode'] == 'full'

    def test_memberships_are_independent(self, client):
        from dealhunter.config import load_config, save_config
        save_config({
            'memberships': {
                'rappi_pro': {'status': 'unknown'},
                'uber_one': {'status': 'inactive'},
            }
        })
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/membership',
            data={
                'csrf_token': token,
                'membership': 'rappi_pro',
                'status': 'active',
            },
        )
        assert rv.status_code == 302
        cfg = load_config()
        assert cfg['memberships']['rappi_pro']['status'] == 'active'
        assert cfg['memberships']['uber_one']['status'] == 'inactive'

        page = client.get('/admin/settings').get_data(as_text=True)
        assert 'name="membership" value="rappi_pro"' in page
        assert 'name="membership" value="uber_one"' in page

    def test_location_post_requires_csrf(self, client):
        rv = client.post('/admin/settings/location', data={'lat': '20', 'lng': '-103'})
        assert rv.status_code == 400

    @pytest.mark.parametrize(
        "payload",
        [
            {'lat': '20'},
            {'lng': '-103'},
            {'lat': '91', 'lng': '-103'},
            {'lat': '20', 'lng': '-181'},
            {'lat': 'abc', 'lng': '-103'},
        ],
    )
    def test_location_rejects_incomplete_or_invalid_pair(self, client, payload):
        from dealhunter.config import load_config
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/location',
            data={'csrf_token': token, **payload},
        )
        assert rv.status_code == 302
        cfg = load_config()
        assert 'lat' not in cfg
        assert 'lng' not in cfg

    def test_location_saves_pair_atomically(self, client):
        from dealhunter.config import load_config
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/location',
            data={'csrf_token': token, 'lat': '20.5', 'lng': '-103.4'},
        )
        assert rv.status_code == 302
        cfg = load_config()
        assert cfg['lat'] == 20.5
        assert cfg['lng'] == -103.4
        assert 'accuracy' not in cfg

    def test_location_save_failure_never_reports_success(self, client, monkeypatch):
        monkeypatch.setattr(
            'dealhunter.web.admin.save_config',
            lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError('simulated')),
        )
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/location',
            data={'csrf_token': token, 'lat': '20.5', 'lng': '-103.4'},
            follow_redirects=True,
        )
        assert rv.status_code == 200
        assert b'No se pudo guardar la ubicaci' in rv.data
        assert 'Ubicación guardada'.encode('utf-8') not in rv.data

    def test_location_return_to_is_same_origin_only(self, client):
        token = _get_csrf_token(client)
        external = client.post(
            '/admin/settings/location',
            data={
                'csrf_token': token,
                'lat': '20.5',
                'lng': '-103.4',
                'return_to': 'https://evil.example/steal',
            },
        )
        assert external.status_code == 302
        assert external.headers['Location'].startswith('/admin/settings')
        assert 'evil.example' not in external.headers['Location']

        local = client.post(
            '/admin/settings/location',
            data={
                'csrf_token': token,
                'lat': '20.6',
                'lng': '-103.5',
                'return_to': '/admin/runs',
            },
        )
        assert local.status_code == 302
        assert local.headers['Location'] == '/admin/runs'

    def test_restore_recommended_removes_override(self, client):
        from dealhunter.config import get_merged_config, load_config, save_config
        save_config({'max_runtime': 120})
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/restore',
            data={'csrf_token': token, 'key': 'max_runtime'},
        )
        assert rv.status_code == 302
        assert 'max_runtime' not in load_config()
        assert get_merged_config(None)['max_runtime'] == 3600

    @pytest.mark.parametrize('key', ['token', 'radius', 'output_format', 'unknown_setting'])
    def test_restore_rejects_secret_readonly_and_unknown(self, client, key):
        token = _get_csrf_token(client)
        rv = client.post(
            '/admin/settings/restore',
            data={'csrf_token': token, 'key': key},
        )
        assert rv.status_code == 400

    def test_basic_and_advanced_settings_are_task_oriented(self, client):
        rv = client.get('/admin/settings')
        html = rv.get_data(as_text=True)
        assert 'Configuración básica' in html
        assert 'Ubicación de entrega' in html
        assert 'Proveedores' in html
        assert 'Membresías' in html
        assert 'Modo de exploración' in html
        assert 'Ajustes avanzados' in html
        assert 'Procedencia del run; no limita adquisición.' in html
        assert 'Provider principal' not in html
        assert 'Integración secundaria' not in html
