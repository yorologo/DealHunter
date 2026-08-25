"""Tests for exact-store native Rappi navigation."""

import os
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from dealhunter.web.app import create_app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "open-rappi.db"
    from tests.helpers.db import create_current_schema_db, insert_store
    app = create_app({"TESTING": True, "DATABASE": str(db_path)})
    conn = create_current_schema_db(str(db_path))
    insert_store(conn, '111', name='Tacos Moy Santa Esther', type='restaurants')
    insert_store(conn, '222', name='City Market', type='market')
    insert_store(conn, '333', name='Unsupported Store', type='express_parent')
    insert_store(conn, '444', name='Turbo', type='chiper_home')
    insert_store(conn, '555', name='Turbo Market', type='chiper_extended')
    conn.commit()
    conn.close()
    with app.test_client() as test_client:
        yield test_client


def _csrf(client):
    with client.session_transaction() as session:
        session["csrf_token"] = "test-csrf-token"
    return "test-csrf-token"


def _success_result():
    return MagicMock(returncode=0, stdout="Status: ok\nActivity: com.grability.rappi", stderr="")


def _post(client, store_id="111", **extra):
    data = {"store_id": store_id, "csrf_token": _csrf(client), **extra}
    return client.post(
        "/api/open-rappi",
        data=data,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )


@patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish")
@patch("dealhunter.web.rappi_native.subprocess.run")
def test_open_rappi_native_deeplink_when_supported(mock_run, _mock_which, client):
    mock_run.return_value = _success_result()

    response = _post(client, "111")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    args, kwargs = mock_run.call_args
    assert args[0][:2] == ["/usr/bin/rish", "-c"]
    command = args[0][2]
    assert "gbrappi://com.grability.rappi?store_type=restaurant&store_id=111" in command
    assert "-p com.grability.rappi" in command
    assert "android.intent.action.VIEW" in command
    assert kwargs["shell"] is False


@patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish")
@patch("dealhunter.web.rappi_native.subprocess.run")
def test_market_uses_native_store_id(mock_run, _mock_which, client):
    mock_run.return_value = _success_result()

    response = _post(client, "222")

    assert response.status_code == 200
    command = mock_run.call_args.args[0][2]
    assert "store_type=market&store_id=222" in command


@pytest.mark.parametrize(
    ("store_id", "native_type"),
    (("444", "chiper_home"), ("555", "chiper_extended")),
)
@patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish")
@patch("dealhunter.web.rappi_native.subprocess.run")
def test_turbo_store_types_use_verified_native_ids(
    mock_run, _mock_which, store_id, native_type, client
):
    mock_run.return_value = _success_result()

    response = _post(client, store_id)

    assert response.status_code == 200
    command = mock_run.call_args.args[0][2]
    assert f"store_type={native_type}&store_id={store_id}" in command


@patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish")
@patch("dealhunter.web.rappi_native.subprocess.run")
def test_open_rappi_never_uses_browser(mock_run, _mock_which, client):
    mock_run.return_value = _success_result()

    response = _post(client)

    assert response.status_code == 200
    command = mock_run.call_args.args[0][2].casefold()
    assert "http://" not in command
    assert "https://" not in command
    assert "rappi.com.mx" not in command
    assert "launcher" not in command
    assert "termux-open" not in command
    assert "chrome" not in command


@patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish")
@patch("dealhunter.web.rappi_native.subprocess.run")
def test_open_rappi_store_lookup_is_server_side(mock_run, _mock_which, client):
    mock_run.return_value = _success_result()

    response = _post(
        client,
        "111",
        store_name="attacker supplied name",
        store_type="market",
        url="https://example.invalid",
    )

    assert response.status_code == 200
    command = mock_run.call_args.args[0][2]
    assert "store_type=restaurant&store_id=111" in command
    assert "attacker" not in command
    assert "example.invalid" not in command


@patch("dealhunter.web.rappi_native.subprocess.run")
def test_open_rappi_rejects_unknown_store(mock_run, client):
    response = _post(client, "999")

    assert response.status_code == 404
    assert response.get_json()["ok"] is False
    mock_run.assert_not_called()


@patch("dealhunter.web.rappi_native.subprocess.run")
def test_unsupported_store_type_fails_safely(mock_run, client):
    response = _post(client, "333")

    assert response.status_code == 422
    assert response.get_json()["ok"] is False
    mock_run.assert_not_called()


@patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish")
@patch("dealhunter.web.rappi_native.subprocess.run")
def test_open_rappi_launcher_failure(mock_run, _mock_which, client):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error: Activity not started")

    response = _post(client)

    assert response.status_code == 502
    assert response.get_json()["ok"] is False
    assert mock_run.call_count == 1


@patch("dealhunter.web.rappi_native.shutil.which", return_value=None)
def test_shizuku_shell_missing_fails_closed(_mock_which, client):
    response = _post(client)

    assert response.status_code == 502
    assert response.get_json()["ok"] is False


def test_navigation_lock_rejects_concurrent_request(client):
    from dealhunter.web.rappi_native import NAVIGATION_LOCK

    assert NAVIGATION_LOCK.acquire(blocking=False)
    try:
        with patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish"):
            response = _post(client)
    finally:
        NAVIGATION_LOCK.release()

    assert response.status_code == 409
    assert response.get_json()["ok"] is False


def test_missing_csrf_rejected(client):
    response = client.post(
        "/api/open-rappi",
        data={"store_id": "111"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 400


def test_invalid_csrf_rejected(client):
    response = client.post(
        "/api/open-rappi",
        data={"store_id": "111", "csrf_token": "forged"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 400


def test_missing_store_id(client):
    response = _post(client, "")
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_non_numeric_store_id_rejected(client):
    response = _post(client, "../etc/passwd")
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


@patch("dealhunter.web.rappi_native.shutil.which", return_value="/usr/bin/rish")
@patch("dealhunter.web.rappi_native.subprocess.run")
def test_non_ajax_redirects_back_not_to_rappi(mock_run, _mock_which, client):
    mock_run.return_value = _success_result()
    token = _csrf(client)

    response = client.post(
        "/api/open-rappi",
        data={"store_id": "111", "csrf_token": token},
        headers={"Referer": "/restaurants/111"},
    )

    assert response.status_code == 302
    assert "rappi.com.mx" not in response.location
