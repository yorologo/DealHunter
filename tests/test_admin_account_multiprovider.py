from unittest.mock import patch
import json
import time

import pytest


RAPPI_LOCAL = {
    "configured": True,
    "status": "CONFIGURED",
    "source": "PERSISTENT",
    "last_validated_at": None,
    "action_required": None,
    "market": "UNKNOWN",
    "region": "UNKNOWN",
    "has_prime": False,
    "prime_type": "NONE",
    "effective": True,
}

UBER_LOCAL = {
    "provider": "Uber Eats",
    "profile": "CONFIGURED",
    "runtime": "RUNTIME_STOPPED",
    "session": "UNVERIFIED",
    "last_sync": "Never",
    "last_sync_age_hours": None,
    "data_status": "NO_DATA",
    "status": "UNVERIFIED",
    "checked_network": False,
}

@pytest.fixture
def client(tmp_path):
    from dealhunter.db import setup_db
    from dealhunter.web.app import create_app

    db_path = str(tmp_path / "account-web.db")
    setup_db(db_path).close()
    app = create_app({"TESTING": True, "DATABASE": db_path})
    with app.test_client() as web_client:
        yield web_client



def csrf_token(client):
    client.get("/admin/account")
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_account_renders_rappi_and_uber(client):
    with patch("dealhunter.account.get_account_status", return_value=RAPPI_LOCAL), \
         patch("dealhunter.providers.uber_eats.status.get_status", return_value=UBER_LOCAL):
        rv = client.get("/admin/account")
    assert rv.status_code == 200
    assert b"Cuentas / Proveedores" in rv.data
    assert b"Rappi" in rv.data
    assert b"Uber Eats" in rv.data
    assert b"rappi-account-card" in rv.data
    assert b"uber-account-card" in rv.data


def test_account_get_is_local_only_for_both_providers(client, monkeypatch):
    calls = []

    def rappi(config, check_network=False):
        calls.append(("rappi", check_network))
        return RAPPI_LOCAL

    def uber(check_network=False, db_path=None):
        calls.append(("uber", check_network))
        return UBER_LOCAL

    monkeypatch.setattr("dealhunter.account.get_account_status", rappi)
    monkeypatch.setattr("dealhunter.providers.uber_eats.status.get_status", uber)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("GET account must not use HTTP")),
    )

    rv = client.get("/admin/account")
    assert rv.status_code == 200
    assert calls == [("rappi", False), ("uber", False)]


def test_rappi_explicit_check_only_network_validates_rappi(client, monkeypatch):
    calls = []

    def rappi(config, check_network=False):
        calls.append(("rappi", check_network))
        return {**RAPPI_LOCAL, "status": "VALID"}

    def uber(check_network=False, db_path=None):
        calls.append(("uber", check_network))
        return UBER_LOCAL

    monkeypatch.setattr("dealhunter.account.get_account_status", rappi)
    monkeypatch.setattr("dealhunter.providers.uber_eats.status.get_status", uber)
    token = csrf_token(client)
    calls.clear()
    rv = client.post("/admin/account/check", headers={"X-CSRF-Token": token})
    assert rv.status_code == 200
    assert calls == [("rappi", True), ("uber", False)]
    assert b"VALID" in rv.data


def test_uber_explicit_check_only_network_validates_uber(client, monkeypatch):
    calls = []

    def rappi(config, check_network=False):
        calls.append(("rappi", check_network))
        return RAPPI_LOCAL

    def uber(check_network=False, db_path=None):
        calls.append(("uber", check_network))
        return {**UBER_LOCAL, "status": "READY", "session": "VALID", "checked_network": True}

    monkeypatch.setattr("dealhunter.account.get_account_status", rappi)
    monkeypatch.setattr("dealhunter.providers.uber_eats.status.get_status", uber)
    token = csrf_token(client)
    calls.clear()
    rv = client.post("/admin/account/uber/check", headers={"X-CSRF-Token": token})
    assert rv.status_code == 200
    assert calls == [("rappi", False), ("uber", True)]
    assert b"READY" in rv.data
    assert b"VALID" in rv.data


def test_uber_check_requires_post_and_csrf(client):
    assert client.get("/admin/account/uber/check").status_code == 405
    assert client.post("/admin/account/uber/check").status_code == 400


def test_rappi_invalidate_still_uses_session_service(client, monkeypatch):
    state = {"invalidated": False}

    class FakeSessionService:
        def delete(self):
            state["invalidated"] = True
            return True

    monkeypatch.setattr("dealhunter.secret_store.SessionService", FakeSessionService)
    token = csrf_token(client)
    rv = client.post("/admin/account/delete", headers={"X-CSRF-Token": token})
    assert rv.status_code in (302, 303)
    assert state["invalidated"] is True
    assert rv.headers["Location"].endswith("/admin/account")


def test_uber_error_does_not_break_rappi(client, monkeypatch):
    monkeypatch.setattr("dealhunter.account.get_account_status", lambda *a, **k: {**RAPPI_LOCAL, "status": "VALID"})
    monkeypatch.setattr(
        "dealhunter.providers.uber_eats.status.get_status",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("UBER_SECRET_FAILURE")),
    )
    rv = client.get("/admin/account")
    assert rv.status_code == 200
    assert b"Rappi" in rv.data and b"VALID" in rv.data
    assert b"Uber Eats" in rv.data and b"RUNTIME_ERROR" in rv.data
    assert b"UBER_SECRET_FAILURE" not in rv.data


def test_rappi_error_does_not_break_uber(client, monkeypatch):
    monkeypatch.setattr(
        "dealhunter.account.get_account_status",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("RAPPI_SECRET_FAILURE")),
    )
    monkeypatch.setattr("dealhunter.providers.uber_eats.status.get_status", lambda *a, **k: {**UBER_LOCAL, "status": "READY", "session": "VALID"})
    rv = client.get("/admin/account")
    assert rv.status_code == 200
    assert b"Rappi" in rv.data and b"ERROR" in rv.data
    assert b"Uber Eats" in rv.data and b"READY" in rv.data
    assert b"RAPPI_SECRET_FAILURE" not in rv.data


def test_account_html_never_exposes_provider_secrets(client, monkeypatch):
    rappi = {**RAPPI_LOCAL, "token": "SUPER_SECRET_RAPPI_TOKEN"}
    uber = {
        **UBER_LOCAL,
        "cookie": "SUPER_SECRET_UBER_COOKIE",
        "profile_path": "/secret/profile/SUPER_SECRET_PROFILE",
    }
    monkeypatch.setattr("dealhunter.account.get_account_status", lambda *a, **k: rappi)
    monkeypatch.setattr("dealhunter.providers.uber_eats.status.get_status", lambda *a, **k: uber)
    rv = client.get("/admin/account")
    assert rv.status_code == 200
    assert b"SUPER_SECRET_RAPPI_TOKEN" not in rv.data
    assert b"SUPER_SECRET_UBER_COOKIE" not in rv.data
    assert b"SUPER_SECRET_PROFILE" not in rv.data
    assert b"dealhunter uber setup" in rv.data or b"Comprobar sesi" in rv.data


def test_uber_needs_login_shows_terminal_setup_instruction(client, monkeypatch):
    uber = {**UBER_LOCAL, "profile": "NOT_CONFIGURED", "status": "NEEDS_LOGIN", "session": "NEEDS_LOGIN"}
    monkeypatch.setattr("dealhunter.account.get_account_status", lambda *a, **k: RAPPI_LOCAL)
    monkeypatch.setattr("dealhunter.providers.uber_eats.status.get_status", lambda *a, **k: uber)
    rv = client.get("/admin/account")
    assert b"dealhunter uber setup" in rv.data
    assert b"Start Chromium" not in rv.data
    assert b"Stop Chromium" not in rv.data



def _start_rappi_mobile(client):
    token = csrf_token(client)
    rv = client.post(
        "/admin/account/rappi/mobile/start",
        headers={"X-CSRF-Token": token},
    )
    assert rv.status_code == 200
    with client.session_transaction() as flask_session:
        state = dict(flask_session["rappi_mobile_auth"])
    return token, state, rv


def _commit_mobile(client, csrf, nonce, token="MOBILE_RAPPI_TOKEN_123456789"):
    return client.post(
        "/admin/account/rappi/mobile/commit",
        json={"nonce": nonce, "token": token},
        headers={"X-CSRF-Token": csrf},
    )


def test_account_get_does_not_create_mobile_nonce(client, monkeypatch):
    monkeypatch.setattr("dealhunter.account.get_account_status", lambda *a, **k: RAPPI_LOCAL)
    monkeypatch.setattr("dealhunter.providers.uber_eats.status.get_status", lambda *a, **k: UBER_LOCAL)
    rv = client.get("/admin/account")
    assert rv.status_code == 200
    with client.session_transaction() as flask_session:
        assert "rappi_mobile_auth" not in flask_session


def test_mobile_start_requires_csrf(client):
    assert client.post("/admin/account/rappi/mobile/start").status_code == 400


def test_mobile_start_generates_loopback_fragment_bookmarklet(client):
    _, state, rv = _start_rappi_mobile(client)
    assert state["nonce"]
    assert state["expires_at"] > time.time()
    assert b"Configurar desde este tel" in rv.data
    assert (b"http://localhost" in rv.data or b"http://127.0.0.1" in rv.data)
    assert b"/admin/account/rappi/mobile/import" in rv.data
    assert b"#" in rv.data
    assert b"?token=" not in rv.data


def test_mobile_import_page_uses_fragment_and_clears_it(client):
    _start_rappi_mobile(client)
    rv = client.get("/admin/account/rappi/mobile/import")
    assert rv.status_code == 200
    assert b"location.hash" in rv.data
    assert b"history.replaceState" in rv.data
    assert b"/admin/account/rappi/mobile/commit" in rv.data
    assert rv.headers["Referrer-Policy"] == "no-referrer"


def test_mobile_commit_requires_csrf(client):
    _, state, _ = _start_rappi_mobile(client)
    rv = client.post(
        "/admin/account/rappi/mobile/commit",
        json={"nonce": state["nonce"], "token": "MOBILE_RAPPI_TOKEN_123456789"},
    )
    assert rv.status_code == 400


def test_mobile_commit_rejects_missing_flow(client):
    csrf = csrf_token(client)
    rv = _commit_mobile(client, csrf, "missing")
    assert rv.status_code == 400
    assert rv.get_json()["error"] == "FLOW_NOT_STARTED"


def test_mobile_commit_rejects_invalid_nonce(client):
    csrf, _, _ = _start_rappi_mobile(client)
    rv = _commit_mobile(client, csrf, "wrong-nonce")
    assert rv.status_code == 400
    assert rv.get_json()["error"] == "INVALID_NONCE"


def test_mobile_commit_rejects_expired_nonce(client):
    csrf, state, _ = _start_rappi_mobile(client)
    with client.session_transaction() as flask_session:
        flask_session["rappi_mobile_auth"] = {**state, "expires_at": time.time() - 1}
    rv = _commit_mobile(client, csrf, state["nonce"])
    assert rv.status_code == 400
    assert rv.get_json()["error"] == "NONCE_EXPIRED"
    with client.session_transaction() as flask_session:
        assert "rappi_mobile_auth" not in flask_session


def test_mobile_commit_rejects_malformed_payload(client):
    csrf, _, _ = _start_rappi_mobile(client)
    rv = client.post(
        "/admin/account/rappi/mobile/commit",
        data=b"{malformed",
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert rv.status_code == 400
    assert rv.get_json()["error"] == "MALFORMED_PAYLOAD"


def test_mobile_commit_rejects_oversized_payload(client):
    csrf, state, _ = _start_rappi_mobile(client)
    rv = client.post(
        "/admin/account/rappi/mobile/commit",
        data=json.dumps({"nonce": state["nonce"], "token": "x" * (70 * 1024)}),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert rv.status_code == 413
    assert rv.get_json()["error"] == "PAYLOAD_TOO_LARGE"


def test_mobile_commit_rejects_missing_token(client):
    csrf, state, _ = _start_rappi_mobile(client)
    rv = client.post(
        "/admin/account/rappi/mobile/commit",
        json={"nonce": state["nonce"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert rv.status_code == 400
    assert rv.get_json()["error"] == "TOKEN_MISSING"


def test_mobile_commit_secret_store_failure_is_not_success(client, monkeypatch, caplog):
    class FailingService:
        def store_persistent(self, token):
            raise RuntimeError("storage unavailable")

    monkeypatch.setattr("dealhunter.secret_store.SessionService", FailingService)
    csrf, state, _ = _start_rappi_mobile(client)
    secret = "MOBILE_SECRET_MUST_NOT_LEAK_123456"
    rv = _commit_mobile(client, csrf, state["nonce"], secret)
    assert rv.status_code == 500
    assert rv.get_json()["error"] == "SECRET_STORE_ERROR"
    assert secret not in rv.get_data(as_text=True)
    assert secret not in caplog.text
    with client.session_transaction() as flask_session:
        assert flask_session["rappi_mobile_auth"]["nonce"] == state["nonce"]


@pytest.mark.parametrize("status", ["VALID", "UNVERIFIED", "EXPIRED", "ERROR"])
def test_mobile_post_import_uses_canonical_account_status(client, monkeypatch, status):
    stored = []

    class FakeService:
        def store_persistent(self, token):
            stored.append(token)
            return True

    monkeypatch.setattr("dealhunter.secret_store.SessionService", FakeService)
    monkeypatch.setattr(
        "dealhunter.web.admin.get_account_status",
        lambda *a, **k: {"status": status},
    )
    csrf, state, _ = _start_rappi_mobile(client)
    rv = _commit_mobile(client, csrf, state["nonce"])
    assert rv.status_code == 200
    assert stored == ["MOBILE_RAPPI_TOKEN_123456789"]
    assert rv.get_json()["status"] == status
    with client.session_transaction() as flask_session:
        assert "rappi_mobile_auth" not in flask_session


def test_mobile_nonce_is_single_use_and_replay_rejected(client, monkeypatch):
    class FakeService:
        def store_persistent(self, token):
            return True

    monkeypatch.setattr("dealhunter.secret_store.SessionService", FakeService)
    monkeypatch.setattr(
        "dealhunter.web.admin.get_account_status",
        lambda *a, **k: {"status": "VALID"},
    )
    csrf, state, _ = _start_rappi_mobile(client)
    first = _commit_mobile(client, csrf, state["nonce"])
    second = _commit_mobile(client, csrf, state["nonce"])
    assert first.status_code == 200
    assert second.status_code == 400
    assert second.get_json()["error"] == "FLOW_NOT_STARTED"


def test_mobile_persistent_storage_is_encrypted(client, monkeypatch):
    from dealhunter.secret_store import SessionService, SESSION_PERSISTENT

    monkeypatch.setattr(
        "dealhunter.web.admin.get_account_status",
        lambda *a, **k: {"status": "UNVERIFIED"},
    )
    csrf, state, _ = _start_rappi_mobile(client)
    secret = "ENCRYPTED_MOBILE_RAPPI_TOKEN_123456789"
    rv = _commit_mobile(client, csrf, state["nonce"], secret)
    assert rv.status_code == 200
    svc = SessionService()
    assert svc.get_mode() == SESSION_PERSISTENT
    encrypted = open(svc.store.session_file, "rb").read()
    assert secret.encode() not in encrypted


def test_mobile_token_never_appears_in_response_redirect_or_log(client, monkeypatch, caplog):
    class FakeService:
        def store_persistent(self, token):
            return True

    monkeypatch.setattr("dealhunter.secret_store.SessionService", FakeService)
    monkeypatch.setattr(
        "dealhunter.web.admin.get_account_status",
        lambda *a, **k: {"status": "VALID"},
    )
    csrf, state, _ = _start_rappi_mobile(client)
    secret = "NO_RENDER_NO_LOG_MOBILE_TOKEN_123456789"
    rv = _commit_mobile(client, csrf, state["nonce"], secret)
    assert secret not in rv.get_data(as_text=True)
    assert secret not in str(rv.headers)
    assert secret not in caplog.text


def test_account_exposes_mobile_and_pc_rappi_methods_without_changing_uber(client):
    rv = client.get("/admin/account")
    assert rv.status_code == 200
    assert b"Configurar desde este tel" in rv.data
    assert b"Usar asistente de navegador" in rv.data
    assert b"/admin/catalog-sync/wizard?return_path=/admin/account" in rv.data
    assert b"Uber Eats" in rv.data
    assert b"dealhunter uber setup" in rv.data or b"Comprobar sesi" in rv.data



def test_mobile_start_preserves_loopback_host_for_session_cookie(client):
    token = csrf_token(client)
    rv = client.post(
        "/admin/account/rappi/mobile/start",
        base_url="http://localhost:8765",
        headers={"X-CSRF-Token": token},
    )
    assert rv.status_code == 200
    assert b"http://localhost:8765/admin/account/rappi/mobile/import" in rv.data


def test_mobile_start_cross_host_is_rejected_by_csrf_session_boundary(client):
    token = csrf_token(client)
    rv = client.post(
        "/admin/account/rappi/mobile/start",
        base_url="http://evil.example:8765",
        headers={"X-CSRF-Token": token},
    )
    assert rv.status_code == 400
    assert b"evil.example" not in rv.data



def test_mobile_fragment_secret_is_never_rendered_server_side(client):
    _start_rappi_mobile(client)
    secret = "FRAGMENT_SECRET_MUST_STAY_CLIENT_SIDE"
    rv = client.get(f"/admin/account/rappi/mobile/import#{secret}")
    assert rv.status_code == 200
    assert secret.encode() not in rv.data
    assert b"location.hash" in rv.data
