import subprocess
from pathlib import Path

import dealhunter.cli as cli
import dealhunter.scheduler as scheduler
import dealhunter.web.app as web_app


ROOT = Path(__file__).resolve().parents[1]


def test_web_command_uses_installed_cli_without_opening_db(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "get_merged_config", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "setup_db", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("CLI should delegate DB init to run_server")))
    monkeypatch.setattr(web_app, "run_server", lambda port=8765, debug=False: seen.update(port=port))

    cli.main(["web", "--port", "9876"])

    assert seen == {"port": 9876}


def test_scheduler_command_reuses_scheduler_service_without_db(monkeypatch, capsys):
    state = {"enabled": False}
    config = {"lat": 20.7, "lng": -103.4}
    monkeypatch.setattr(cli, "get_merged_config", lambda *args, **kwargs: config)
    monkeypatch.setattr(cli, "setup_db", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("scheduler CLI must not open SQLite")))
    monkeypatch.setattr(scheduler, "enable_scheduler", lambda cfg=None: state.update(enabled=True, config=cfg))
    monkeypatch.setattr(scheduler, "disable_scheduler", lambda: state.update(enabled=False))
    monkeypatch.setattr(scheduler, "is_scheduler_enabled", lambda: state["enabled"])
    monkeypatch.setattr(scheduler, "get_next_run", lambda: None)

    cli.main(["scheduler", "enable"])
    assert state["enabled"] is True
    assert state["config"] == config
    assert "scheduler=enabled" in capsys.readouterr().out

    cli.main(["scheduler", "disable"])
    assert state["enabled"] is False
    assert "scheduler=disabled" in capsys.readouterr().out


def test_install_and_update_scripts_have_safe_kiss_contract():
    install = ROOT / "install.sh"
    update = ROOT / "update.sh"
    for script in (install, update):
        result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    install_text = install.read_text()
    update_text = update.read_text()
    assert "pip install ." in install_text
    assert "requirements.txt" not in install_text
    assert "pkg upgrade" not in install_text
    assert "git status --porcelain" in update_text
    assert "git merge --ff-only origin/main" in update_text
    assert "git reset --hard" not in update_text
    assert "git switch --detach" in update_text
    assert "git switch main" in update_text
    assert "dealhunter db backup" in update_text
    assert "dealhunter db integrity" in update_text
    ignore_text = (ROOT / ".gitignore").read_text().splitlines()
    assert "build/" in ignore_text
    assert "*.egg-info/" in ignore_text


def test_integrity_and_backup_do_not_create_missing_database(tmp_path, capsys, monkeypatch):
    from dealhunter.db import backup_db, db_integrity, db_vacuum

    db_path = tmp_path / "fresh" / "dealhunter.db"
    assert db_integrity(str(db_path)) == "not_initialized"
    assert backup_db(str(db_path)) is None
    assert db_vacuum(str(db_path)) is False
    assert not db_path.exists()

    monkeypatch.setenv("RAPPI_DB_PATH", str(db_path))
    cli.main(["db", "backup"])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "nothing to back up" in captured.err.lower()
    assert not db_path.exists()


def test_v331_upgrade_bootstrap_is_documented_before_update_sh():
    readme = (ROOT / "README.md").read_text()
    operations = (ROOT / "docs" / "operations.md").read_text()
    for text in (readme, operations):
        assert "v3.3.1" in text
        assert "v3.4.0" in text
        assert "dealhunter db backup" in text
        assert "git merge --ff-only origin/main" in text
        assert "./install.sh" in text
        assert "./update.sh" in text
