from dealhunter.config import load_config
from dealhunter.db import setup_db
from dealhunter.web.app import create_app


def _client(tmp_path, monkeypatch):
    config_home = tmp_path / 'xdg-config'
    db_path = tmp_path / 'admin.db'
    monkeypatch.setenv('XDG_CONFIG_HOME', str(config_home))
    monkeypatch.setenv('RAPPI_DB_PATH', str(db_path))
    setup_db(str(db_path)).close()
    app = create_app({'DATABASE': str(db_path), 'TESTING': True, 'SECRET_KEY': 'test'})
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['csrf_token'] = 'token'
    return client


def test_admin_provider_rejects_unknown_name_without_persisting(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    before = load_config()
    rv = client.post('/admin/settings/provider', data={
        'csrf_token': 'token', 'provider': 'made_up', 'enabled': 'true'
    })
    assert rv.status_code == 400
    assert load_config() == before


def test_admin_provider_unknown_boolean_does_not_become_false(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    before = load_config()
    rv = client.post('/admin/settings/provider', data={
        'csrf_token': 'token', 'provider': 'rappi', 'enabled': 'maybe'
    })
    assert rv.status_code == 400
    assert load_config() == before


def test_admin_membership_rejects_unknown_name_and_status(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    before = load_config()
    for payload in (
        {'membership': 'vip_magic', 'status': 'active'},
        {'membership': 'rappi_pro', 'status': 'maybe'},
    ):
        rv = client.post('/admin/settings/membership', data={'csrf_token': 'token', **payload})
        assert rv.status_code == 400
        assert load_config() == before


def test_admin_comparison_rejects_unknown_policy(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    before = load_config()
    rv = client.post('/admin/settings/comparison', data={
        'csrf_token': 'token', 'policy': 'rank_everything'
    })
    assert rv.status_code == 400
    assert load_config() == before


def test_admin_settings_unknown_boolean_is_explicit_error_and_no_write(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    before = load_config()
    rv = client.post('/admin/settings/update', data={
        'csrf_token': 'token', 'key': 'compact', 'value': 'maybe'
    })
    assert rv.status_code == 400
    assert b'inv' in rv.data.lower()
    assert load_config() == before


def test_wizard_external_return_path_is_rejected_before_storing(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    class NeverStore:
        def __init__(self, *args, **kwargs):
            pass
        def store_temporary(self, token):
            raise AssertionError('unsafe return_path must be rejected before storing')

    monkeypatch.setattr('dealhunter.secret_store.SessionService', NeverStore)
    for target in ('https://evil.example/x', '//evil.example/x'):
        rv = client.post('/admin/catalog-sync/wizard/store', data={
            'csrf_token': 'token', 'token': 'x', 'session_mode': 'temporary',
            'return_path': target,
        })
        assert rv.status_code == 400


def test_wizard_accepts_internal_return_path(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    class FakeService:
        def __init__(self, *args, **kwargs):
            pass
        def store_temporary(self, token):
            self.token = token

    monkeypatch.setattr('dealhunter.secret_store.SessionService', FakeService)
    monkeypatch.setattr('dealhunter.account.get_account_status', lambda *a, **k: {'status': 'VALID'})
    rv = client.post('/admin/catalog-sync/wizard/store', data={
        'csrf_token': 'token', 'token': 'x', 'session_mode': 'temporary',
        'return_path': '/admin/account',
    })
    assert rv.status_code == 302
    assert rv.headers['Location'].endswith('/admin/account')


def test_open_rappi_never_redirects_external_referrer(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    rv = client.post('/api/open-rappi', data={
        'csrf_token': 'token', 'store_id': 'invalid'
    }, headers={'Referer': 'https://evil.example/phish'})
    assert rv.status_code == 302
    assert 'evil.example' not in rv.headers['Location']



def test_wizard_from_account_preserves_account_return_path(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    rv = client.get('/admin/catalog-sync/wizard?return_path=/admin/account')
    assert rv.status_code == 200
    assert b'name="return_path" value="/admin/account"' in rv.data
    assert b'M\xc3\xa9todo PC / navegador' in rv.data


def test_wizard_external_get_return_path_falls_back_local(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    rv = client.get('/admin/catalog-sync/wizard?return_path=https://evil.example/x')
    assert rv.status_code == 200
    assert b'evil.example' not in rv.data
    assert b'name="return_path" value="/admin/catalog-sync"' in rv.data
