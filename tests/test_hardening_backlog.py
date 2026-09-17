import math
import os
import sqlite3
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from dealhunter.config import get_config_path, load_config, save_config
from dealhunter.core import process_and_insert_product
from dealhunter.db import CURRENT_SCHEMA_VERSION, backup_db
from dealhunter.errors import DealHunterError
from dealhunter.secret_store import SecretStore
from dealhunter.web.app import create_app


def _product(product_id, name, category=None):
    return {"id": product_id, "name": name, "price": 10, "category": category, "memberships": []}


def test_missing_structured_category_stays_unknown_and_preserves_trusted_value(current_schema_db):
    seen = set()
    process_and_insert_product(_product("p1", "Hamburguesa especial"), "run-1", "s1", "Super Market", {}, None, current_schema_db, seen)
    row = current_schema_db.execute("SELECT category, category_source FROM products WHERE product_id = 'p1'").fetchone()
    assert row == (None, "unknown")

    seen.clear()
    process_and_insert_product(_product("p1", "Hamburguesa especial", "Comida preparada"), "run-2", "s1", "Super Market", {}, None, current_schema_db, seen)
    seen.clear()
    process_and_insert_product(_product("p1", "Hamburguesa especial"), "run-3", "s1", "Super Market", {}, None, current_schema_db, seen)
    row = current_schema_db.execute("SELECT category, category_source FROM products WHERE product_id = 'p1'").fetchone()
    assert row == ("Comida preparada", "provider")


def test_malformed_toml_raises_structured_config_error():
    path = Path(get_config_path())
    path.parent.mkdir(parents=True)
    path.write_text("broken = [", encoding="utf-8")
    with pytest.raises(DealHunterError) as exc:
        load_config()
    assert exc.value.code == "CONFIG_ERROR"


def test_config_read_oserror_is_structured(monkeypatch):
    path = Path(get_config_path())
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr("builtins.open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("permission denied")))
    with pytest.raises(DealHunterError) as exc:
        load_config()
    assert exc.value.code == "CONFIG_ERROR"


def test_config_round_trips_escaped_strings_and_rejects_unsafe_values():
    value = 'quote " slash \\ newline\n tab\t'
    save_config({"label": value, "nested section": {"enabled": True}})
    assert load_config() == {"label": value, "nested section": {"enabled": True}}
    for invalid in (math.nan, math.inf, object(), None):
        with pytest.raises(DealHunterError) as exc:
            save_config({"value": invalid})
        assert exc.value.code == "CONFIG_ERROR"


def test_config_replace_failure_leaves_previous_file_intact(monkeypatch):
    save_config({"value": "old"})
    path = Path(get_config_path())
    before = path.read_bytes()
    monkeypatch.setattr("dealhunter.config.os.replace", lambda *_args: (_ for _ in ()).throw(OSError("replace failed")))
    with pytest.raises(DealHunterError) as exc:
        save_config({"value": "new"})
    assert exc.value.code == "CONFIG_ERROR"
    assert path.read_bytes() == before
    assert list(path.parent.glob(".config.toml.*.tmp")) == []


def test_secret_store_fails_closed_without_cryptography(tmp_path, monkeypatch):
    monkeypatch.setattr("dealhunter.secret_store.CRYPTO_AVAILABLE", False)
    store = SecretStore(str(tmp_path))
    with pytest.raises(DealHunterError) as exc:
        store.store("must-not-hit-disk")
    assert exc.value.code == "SECRET_STORE_UNAVAILABLE"
    assert not (tmp_path / "session.enc").exists()
    assert not (tmp_path / ".session_salt").exists()


def test_flask_secret_is_persistent_private_and_environment_overrides(monkeypatch):
    first = create_app({"TESTING": True})
    second = create_app({"TESTING": True})
    assert first.secret_key == second.secret_key
    assert first.secret_key != "dev"
    secret_path = Path(os.environ["XDG_CONFIG_HOME"]) / "dealhunter" / "flask_secret.key"
    assert secret_path.is_file()
    assert stat.S_IMODE(secret_path.stat().st_mode) == 0o600

    monkeypatch.setenv("SECRET_KEY", "environment-secret")
    assert create_app({"TESTING": True}).secret_key == "environment-secret"


def test_explicit_test_secret_does_not_create_persistent_key():
    secret_path = Path(os.environ["XDG_CONFIG_HOME"]) / "dealhunter" / "flask_secret.key"
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret"})
    assert app.secret_key == "test-only-secret"
    assert not secret_path.exists()


def test_sqlite_backup_is_reopened_and_validated(current_schema_db_path):
    backup = backup_db(current_schema_db_path, tag="verified")
    with sqlite3.connect(backup) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == CURRENT_SCHEMA_VERSION


def test_invalid_sqlite_backup_is_removed(current_schema_db_path, monkeypatch):
    monkeypatch.setattr("dealhunter.db._backup_is_valid", lambda *_args: False)
    with pytest.raises(DealHunterError) as exc:
        backup_db(current_schema_db_path, tag="invalid")
    assert exc.value.code == "DB_CORRUPT"
    assert list(Path(current_schema_db_path).parent.glob("*.invalid.bak")) == []


def _fake_crontab(monkeypatch, scheduler, initial):
    installed = {"content": initial}

    def run(command, **kwargs):
        if command == ["crontab", "-l"]:
            return SimpleNamespace(returncode=0, stdout=installed["content"], stderr="")
        if command == ["crontab", "-"]:
            installed["content"] = kwargs["input"]
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(command)

    monkeypatch.setattr(scheduler.subprocess, "run", run)
    return installed


def test_scheduler_repairs_legacy_entry_and_installs_both_providers(monkeypatch):
    from dealhunter import scheduler

    legacy = (
        "# existing\n"
        "# DealHunter Daily Sweep\n"
        "0 10 * * * cd /data/data/com.termux/files/home/rappi-deal-hunter && "
        "DEALHUNTER_SOURCE=SCHEDULED flock -n /tmp/dealhunter.lock "
        "./bin/rappi-ofertas discover --vertical general\n"
    )
    installed = _fake_crontab(monkeypatch, scheduler, legacy)
    scheduler.enable_scheduler({"lat": 20.0, "lng": -103.0})

    content = installed["content"]
    assert "# existing" in content
    assert "0 7,10,13,19 * * *" in content
    assert "30 7,10,13,19 * * *" in content
    assert "sync --provider rappi" in content
    assert "sync --provider uber_eats" in content
    assert "dealwatcher" in content
    assert "rappi-ofertas" in content
    assert "dealwatcher" in content
    assert str(scheduler.LOG_FILE) in content
    assert "rappi-deal-hunter" not in content
    assert scheduler.is_scheduler_enabled()


def test_scheduler_disable_removes_only_managed_entries(monkeypatch):
    from dealhunter import scheduler

    installed = _fake_crontab(monkeypatch, scheduler, "# existing\n")
    scheduler.enable_scheduler({"lat": 20.0, "lng": -103.0})
    scheduler.disable_scheduler()
    assert installed["content"] == "# existing\n"
    assert not scheduler.is_scheduler_enabled()



def test_scheduler_refuses_enable_without_valid_location(monkeypatch):
    from dealhunter import scheduler

    installed = _fake_crontab(monkeypatch, scheduler, "# existing\n")
    for config in ({}, {"lat": 20.0}, {"lat": float("nan"), "lng": -103.0}, {"lat": 91, "lng": 0}):
        with pytest.raises(RuntimeError, match="Scheduler"):
            scheduler.enable_scheduler(config)
    assert installed["content"] == "# existing\n"


def test_scheduler_rejects_failed_write_and_readback_mismatch(monkeypatch):
    from dealhunter import scheduler

    monkeypatch.setattr(scheduler.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=2, stdout="", stderr="denied"))
    with pytest.raises(RuntimeError, match="denied"):
        scheduler.set_crontab("content\n")

    responses = iter([
        SimpleNamespace(returncode=0, stdout="", stderr=""),
        SimpleNamespace(returncode=0, stdout="different\n", stderr=""),
    ])
    monkeypatch.setattr(scheduler.subprocess, "run", lambda *_args, **_kwargs: next(responses))
    with pytest.raises(RuntimeError, match="verification"):
        scheduler.set_crontab("content\n")


def test_scheduler_does_not_hide_crontab_read_errors(monkeypatch):
    from dealhunter import scheduler

    monkeypatch.setattr(scheduler.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="permission denied"))
    with pytest.raises(RuntimeError, match="permission denied"):
        scheduler.get_crontab()


def test_default_db_path_uses_xdg_data_home_when_no_legacy(monkeypatch, tmp_path):
    from dealhunter.db import get_default_db_path

    monkeypatch.delenv("RAPPI_DB_PATH", raising=False)
    data_home = tmp_path / "xdg-data"
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    assert get_default_db_path() == str(data_home / "dealhunter" / "rappi-deals.db")


def test_default_db_path_preserves_existing_legacy_db(monkeypatch, tmp_path):
    from dealhunter.db import get_default_db_path

    monkeypatch.delenv("RAPPI_DB_PATH", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "new-data"))
    legacy = tmp_path / "rappi-deal-hunter" / "rappi-deals.db"
    legacy.parent.mkdir(parents=True)
    legacy.touch()
    assert get_default_db_path() == str(legacy)


def test_setup_db_creates_missing_parent_for_explicit_path(tmp_path):
    from dealhunter.db import CURRENT_SCHEMA_VERSION, setup_db

    path = tmp_path / "nested" / "data" / "dealhunter.db"
    conn = setup_db(str(path))
    try:
        assert conn.execute("SELECT version FROM schema_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
    finally:
        conn.close()
    assert path.is_file()
