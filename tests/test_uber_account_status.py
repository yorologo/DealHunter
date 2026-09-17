import datetime
import os
import urllib.request

import pytest

from dealhunter.db import setup_db
import dealhunter.providers.uber_eats.status as status_mod


class FakeRuntime:
    instances = []
    initial_running = False
    start_error = None
    profile_path_value = "/nonexistent/uber-profile"

    def __init__(self):
        self.profile_path = type(self).profile_path_value
        self.running = type(self).initial_running
        self.started = False
        self.stopped = False
        type(self).instances.append(self)

    def is_running_local(self):
        return self.running

    def start(self):
        if type(self).start_error:
            raise type(self).start_error
        self.started = True
        self.running = True

    def stop(self):
        self.stopped = True
        self.running = False


@pytest.fixture(autouse=True)
def fake_runtime(monkeypatch):
    FakeRuntime.instances = []
    FakeRuntime.initial_running = False
    FakeRuntime.start_error = None
    FakeRuntime.profile_path_value = "/nonexistent/uber-profile"
    monkeypatch.setattr(status_mod, "ChromiumRuntime", FakeRuntime)


def _profile(tmp_path, exists):
    profile = tmp_path / "uber-profile"
    if exists:
        profile.mkdir()
    FakeRuntime.profile_path_value = str(profile)


def test_local_status_without_profile_is_needs_login_and_no_http(monkeypatch, tmp_path):
    _profile(tmp_path, False)
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("local status must not use HTTP")),
    )
    db_path = tmp_path / "missing" / "dealhunter.db"

    st = status_mod.get_status(check_network=False, db_path=str(db_path))

    assert st["status"] == status_mod.NEEDS_LOGIN
    assert st["session"] == status_mod.NEEDS_LOGIN
    assert st["profile"] == status_mod.PROFILE_NOT_CONFIGURED
    assert st["runtime"] == status_mod.RUNTIME_STOPPED
    assert st["data_status"] == status_mod.NO_DATA
    assert st["checked_network"] is False
    assert not db_path.exists()


def test_local_profile_is_unverified_not_valid(monkeypatch, tmp_path):
    _profile(tmp_path, True)
    st = status_mod.get_status(db_path=str(tmp_path / "missing.db"))
    assert st["profile"] == status_mod.PROFILE_CONFIGURED
    assert st["session"] == status_mod.UNVERIFIED
    assert st["status"] == status_mod.UNVERIFIED


def test_local_runtime_available_without_network(monkeypatch, tmp_path):
    _profile(tmp_path, True)
    FakeRuntime.initial_running = True
    st = status_mod.get_status(db_path=str(tmp_path / "missing.db"))
    assert st["runtime"] == status_mod.READY
    assert st["session"] == status_mod.UNVERIFIED


@pytest.mark.parametrize(
    "session,expected_status",
    [
        (status_mod.VALID, status_mod.READY),
        (status_mod.NEEDS_LOGIN, status_mod.NEEDS_LOGIN),
        (status_mod.UNVERIFIED, status_mod.UNVERIFIED),
    ],
)
def test_explicit_check_maps_transport_session_and_manages_runtime(
    monkeypatch, tmp_path, session, expected_status
):
    _profile(tmp_path, True)

    async def check():
        return session

    monkeypatch.setattr(status_mod, "_check_transport_session", check)
    st = status_mod.get_status(check_network=True, db_path=str(tmp_path / "missing.db"))

    rt = FakeRuntime.instances[-1]
    assert rt.started is True
    assert rt.stopped is True
    assert st["checked_network"] is True
    assert st["session"] == session
    assert st["status"] == expected_status
    assert st["runtime"] == status_mod.RUNTIME_STOPPED


def test_explicit_check_leaves_existing_runtime_running(monkeypatch, tmp_path):
    _profile(tmp_path, True)
    FakeRuntime.initial_running = True

    async def check():
        return status_mod.VALID

    monkeypatch.setattr(status_mod, "_check_transport_session", check)
    st = status_mod.get_status(check_network=True, db_path=str(tmp_path / "missing.db"))
    rt = FakeRuntime.instances[-1]
    assert rt.started is False
    assert rt.stopped is False
    assert st["runtime"] == status_mod.READY
    assert st["session"] == status_mod.VALID


def test_explicit_check_runtime_start_error_fails_closed(monkeypatch, tmp_path):
    _profile(tmp_path, True)
    FakeRuntime.start_error = RuntimeError("chromium unavailable")
    st = status_mod.get_status(check_network=True, db_path=str(tmp_path / "missing.db"))
    assert st["runtime"] == status_mod.RUNTIME_ERROR
    assert st["session"] == status_mod.UNVERIFIED
    assert st["status"] == status_mod.RUNTIME_ERROR


def test_last_sync_current_and_age(monkeypatch, tmp_path):
    _profile(tmp_path, False)
    db_path = tmp_path / "history.db"
    conn = setup_db(str(db_path))
    finished = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)).isoformat().replace("+00:00", "Z")
    conn.execute(
        "INSERT INTO runs (run_id, status, finished_at) VALUES (?, 'SUCCESS', ?)",
        ("uber-sync", finished),
    )
    conn.execute(
        "INSERT INTO stores (provider, store_id, name) VALUES ('uber_eats', 's1', 'Store')"
    )
    conn.execute(
        "INSERT INTO products (provider, store_id, product_id, name) VALUES ('uber_eats', 's1', 'p1', 'Product')"
    )
    conn.execute(
        "INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp) VALUES ('uber-sync', 'uber_eats', 's1', 'p1', 10, ?)",
        (finished,),
    )
    conn.commit()
    conn.close()

    st = status_mod.get_status(db_path=str(db_path))
    assert st["last_sync"] == finished
    assert 2.5 <= st["last_sync_age_hours"] <= 3.5
    assert st["data_status"] == status_mod.CURRENT


def test_last_sync_stale(monkeypatch, tmp_path):
    _profile(tmp_path, False)
    db_path = tmp_path / "stale.db"
    conn = setup_db(str(db_path))
    finished = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=72)).isoformat().replace("+00:00", "Z")
    conn.execute("INSERT INTO runs (run_id, status, finished_at) VALUES (?, 'SUCCESS', ?)", ("uber-old", finished))
    conn.execute("INSERT INTO stores (provider, store_id, name) VALUES ('uber_eats', 's-old', 'Old Store')")
    conn.execute("INSERT INTO products (provider, store_id, product_id, name) VALUES ('uber_eats', 's-old', 'p-old', 'Old Product')")
    conn.execute(
        "INSERT INTO observations (run_id, provider, store_id, product_id, price, timestamp) VALUES ('uber-old', 'uber_eats', 's-old', 'p-old', 10, ?)",
        (finished,),
    )
    conn.commit()
    conn.close()

    st = status_mod.get_status(db_path=str(db_path))
    assert st["last_sync_age_hours"] >= 71
    assert st["data_status"] == status_mod.STALE


def test_no_previous_sync(monkeypatch, tmp_path):
    _profile(tmp_path, False)
    db_path = tmp_path / "empty.db"
    setup_db(str(db_path)).close()
    st = status_mod.get_status(db_path=str(db_path))
    assert st["last_sync"] == "Never"
    assert st["last_sync_age_hours"] is None
    assert st["data_status"] == status_mod.NO_DATA


def test_transport_state_mapping():
    from dealhunter.providers.uber_eats.browser_transport import CHALLENGE_REQUIRED, LOGIN_REQUIRED, READY

    assert status_mod.session_status_from_transport(READY) == status_mod.VALID
    assert status_mod.session_status_from_transport(LOGIN_REQUIRED) == status_mod.NEEDS_LOGIN
    assert status_mod.session_status_from_transport(CHALLENGE_REQUIRED) == status_mod.UNVERIFIED
    assert status_mod.session_status_from_transport("SOMETHING_NEW") == status_mod.UNVERIFIED
