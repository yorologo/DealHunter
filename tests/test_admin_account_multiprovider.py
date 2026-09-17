from unittest.mock import patch

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
        def invalidate(self):
            state["invalidated"] = True

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
