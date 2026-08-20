"""Tests for the native Rappi app launcher (/api/open-rappi).

Verifies that the launcher:
- Uses directed Android Intent with explicit Rappi package
- NEVER falls back to a browser
- Returns JSON for AJAX requests
- Validates CSRF tokens
- Rejects invalid store IDs
- Handles Rappi not being installed gracefully
"""
import pytest
import sys, os
import sqlite3
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from dealhunter.web.app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "DATABASE": "test_open_rappi.db"})
    with app.app_context():
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS stores (store_id TEXT, name TEXT, type TEXT)")
        c.execute("DELETE FROM stores")
        c.execute("INSERT INTO stores VALUES ('111', 'McDonalds', 'restaurant')")
        c.execute("INSERT INTO stores VALUES ('222', 'Chedraui', 'market')")
        c.execute("INSERT INTO stores VALUES ('333', 'Oxxo', 'turbo')")
        conn.commit()
    with app.test_client() as client:
        yield client


def _get_csrf_token(client):
    with client.session_transaction() as sess:
        import secrets
        token = secrets.token_hex(32)
        sess['csrf_token'] = token
    return token


# --- Core: Directed Intent builds correct command ---

@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_restaurant_uses_package_targeted_intent(mock_run, mock_which, client):
    """Intent must target com.grability.rappi explicitly."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent")
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "111", "csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    # Verify the am command included -p com.grability.rappi
    call_args = mock_run.call_args_list[0][0][0]
    assert "-p" in call_args
    assert "com.grability.rappi" in call_args
    assert "android.intent.action.VIEW" in call_args
    assert "https://www.rappi.com.mx/restaurantes/111" in call_args


@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_market_uses_tiendas_url(mock_run, mock_which, client):
    """Market stores use /tiendas/ URL path."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent")
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "222", "csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 200
    call_args = mock_run.call_args_list[0][0][0]
    assert "https://www.rappi.com.mx/tiendas/222" in call_args
    assert "com.grability.rappi" in call_args


# --- No browser fallback ---

@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_never_calls_termux_open_url(mock_run, mock_which, client):
    """termux-open-url must NEVER be called — it opens the browser."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent")
    token = _get_csrf_token(client)
    client.post('/api/open-rappi',
                data={"store_id": "111", "csrf_token": token},
                headers={"X-Requested-With": "XMLHttpRequest"})
    for call in mock_run.call_args_list:
        args = call[0][0]
        assert "termux-open-url" not in args, "termux-open-url must never be used"


@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_never_uses_chrome_package(mock_run, mock_which, client):
    """No subprocess call may reference Chrome or any browser package."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent")
    token = _get_csrf_token(client)
    client.post('/api/open-rappi',
                data={"store_id": "111", "csrf_token": token},
                headers={"X-Requested-With": "XMLHttpRequest"})
    for call in mock_run.call_args_list:
        args = call[0][0]
        for browser in ["com.android.chrome", "org.mozilla.firefox", "com.brave.browser"]:
            assert browser not in args, f"Browser package {browser} must never be used"


@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_no_redirect_to_rappi_website(mock_run, mock_which, client):
    """AJAX response must be JSON, not a redirect to rappi.com.mx."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent")
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "111", "csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/json")
    # Must NOT be a redirect
    assert resp.status_code != 302


# --- Fallback: deep link fails, launcher works ---

@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_fallback_to_launcher_when_deeplink_fails(mock_run, mock_which, client):
    """When VIEW intent fails, fall back to MAIN/LAUNCHER (still Rappi app, not browser)."""
    # First call (VIEW) fails, second call (LAUNCHER) succeeds
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout="Error: Activity not started"),
        MagicMock(returncode=0, stdout="Starting: Intent")
    ]
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "222", "csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "busca manualmente" in data["message"]
    # Second call must be LAUNCHER, still targeting Rappi
    launcher_args = mock_run.call_args_list[1][0][0]
    assert "android.intent.action.MAIN" in launcher_args
    assert "com.grability.rappi" in launcher_args


# --- Rappi not installed ---

@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_rappi_not_reachable(mock_run, mock_which, client):
    """When both intents fail, return clear error — never open browser."""
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout="Error: Activity not started"),
        MagicMock(returncode=1, stdout="Error: Activity not started"),
    ]
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "111", "csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    data = resp.get_json()
    assert data["ok"] is False
    assert "Rappi" in data["error"]


# --- am not available ---

@patch("shutil.which", return_value=None)
def test_am_not_available(mock_which, client):
    """If 'am' command doesn't exist, return error — never use browser fallback."""
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "111", "csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    data = resp.get_json()
    assert data["ok"] is False
    assert "am" in data["error"]


# --- Security: CSRF (handled by before_request middleware, returns 400) ---

def test_missing_csrf_rejected(client):
    resp = client.post('/api/open-rappi',
                       data={"store_id": "111"},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 400


def test_invalid_csrf_rejected(client):
    resp = client.post('/api/open-rappi',
                       data={"store_id": "111", "csrf_token": "forged"},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 400


# --- Security: input validation ---

def test_missing_store_id(client):
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["ok"] is False


def test_non_numeric_store_id_rejected(client):
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "../etc/passwd", "csrf_token": token},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 400


# --- shell=False enforcement ---

@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_shell_false(mock_run, mock_which, client):
    """subprocess.run must always be called with shell=False."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent")
    token = _get_csrf_token(client)
    client.post('/api/open-rappi',
                data={"store_id": "111", "csrf_token": token},
                headers={"X-Requested-With": "XMLHttpRequest"})
    for call in mock_run.call_args_list:
        kwargs = call[1]
        assert kwargs.get("shell") is False or kwargs.get("shell") is None, \
            "subprocess.run must use shell=False"


# --- Non-AJAX: redirect back, not to rappi.com.mx ---

@patch("shutil.which", return_value="/usr/bin/am")
@patch("subprocess.run")
def test_non_ajax_redirects_back_not_to_rappi(mock_run, mock_which, client):
    """Non-AJAX POST must redirect to referrer, NOT to rappi.com.mx."""
    mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent")
    token = _get_csrf_token(client)
    resp = client.post('/api/open-rappi',
                       data={"store_id": "111", "csrf_token": token},
                       headers={"Referer": "/restaurants/111"})
    assert resp.status_code == 302
    assert "rappi.com.mx" not in resp.location
