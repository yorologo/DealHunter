import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import Mock

import pytest

from dealhunter.db import setup_db


REPO_ROOT = Path(__file__).resolve().parents[1]
DEALWATCHER = REPO_ROOT / "bin" / "dealwatcher"
HISTORICO = REPO_ROOT / "bin" / "rappi-historico"
OFERTAS = REPO_ROOT / "bin" / "rappi-ofertas"


def _script_env(tmp_path):
    env = os.environ.copy()
    env["RAPPI_DB_PATH"] = str(tmp_path / "audit.db")
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg-config")
    env.pop("RAPPI_BEARER_TOKEN", None)
    return env


def _load_dealwatcher_module():
    loader = SourceFileLoader("dealwatcher_bin", str(DEALWATCHER))
    spec = importlib.util.spec_from_loader("dealwatcher_bin", loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("argument", ["--help", "--unknown-release-audit-arg"])
def test_dealwatcher_parser_paths_do_not_enter_operational_run(argument):
    module = _load_dealwatcher_module()
    module.run = Mock(side_effect=AssertionError("operational run must not execute"))

    with pytest.raises(SystemExit) as exc:
        module.main([argument])

    assert exc.value.code == (0 if argument == "--help" else 2)
    module.run.assert_not_called()


def test_dealwatcher_help_and_unknown_arg_leave_database_unchanged(tmp_path):
    db_path = tmp_path / "audit.db"
    conn = setup_db(str(db_path))
    conn.execute(
        "INSERT INTO alert_events "
        "(event_key, event_type, store_id, product_id, channel, created_at, delivery_status) "
        "VALUES ('sentinel', 'PRICE_DROP', 'store', 'product', "
        "'PUBLIC', '2026-08-31T00:00:00Z', 'pending')"
    )
    conn.commit()
    conn.close()

    before_stat = db_path.stat()
    before_bytes = db_path.read_bytes()
    with sqlite3.connect(db_path) as conn:
        before_events = conn.execute("SELECT COUNT(*) FROM alert_events").fetchone()[0]

    help_result = subprocess.run(
        [sys.executable, str(DEALWATCHER), "--help"],
        cwd=REPO_ROOT,
        env=_script_env(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    unknown_result = subprocess.run(
        [sys.executable, str(DEALWATCHER), "--unknown-release-audit-arg"],
        cwd=REPO_ROOT,
        env=_script_env(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )

    assert help_result.returncode == 0
    assert "usage:" in help_result.stdout.lower()
    assert unknown_result.returncode == 2
    assert "unrecognized arguments" in unknown_result.stderr.lower()
    assert db_path.read_bytes() == before_bytes
    assert db_path.stat().st_mtime_ns == before_stat.st_mtime_ns
    with sqlite3.connect(db_path) as conn:
        after_events = conn.execute("SELECT COUNT(*) FROM alert_events").fetchone()[0]
    assert after_events == before_events


def test_documented_install_directory_matches_clone_default():
    guide = (REPO_ROOT / "docs" / "installation-termux.md").read_text()
    assert "git clone https://github.com/yorologo/DealHunter.git\ncd DealHunter" in guide
    assert "cd rappi-deal-hunter" not in guide


def test_documented_cli_commands_are_exposed_by_real_parsers(tmp_path):
    docs = (REPO_ROOT / "docs" / "cli.md").read_text()
    assert 'bin/rappi-historico compare "Coca Cola"' in docs
    for stale in (
        "bin/rappi-historico history",
        "bin/rappi-historico watchlist",
        "bin/rappi-historico db status",
    ):
        assert stale not in docs

    env = _script_env(tmp_path)
    commands = (
        (HISTORICO, "compare"),
        (HISTORICO, "deals"),
        (HISTORICO, "alerts"),
        (HISTORICO, "web"),
        (OFERTAS, "watch"),
        (OFERTAS, "db"),
    )
    for script, command in commands:
        result = subprocess.run(
            [sys.executable, str(script), command, "--help"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "usage:" in result.stdout.lower()
