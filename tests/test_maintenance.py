import os
import time
from pathlib import Path
from unittest.mock import patch

from dealhunter.cli import main
from dealhunter.maintenance import cleanup_diagnostics, rotate_file, run_maintenance


def test_rotate_file_is_bounded_and_private(tmp_path):
    log = tmp_path / "crawler-cron.log"
    log.write_bytes(b"x" * 32)
    assert rotate_file(log, max_bytes=8, keep=2) is True
    assert log.read_bytes() == b""
    assert (tmp_path / "crawler-cron.log.1").read_bytes() == b"x" * 32
    assert oct(log.stat().st_mode & 0o777) == "0o600"

    log.write_bytes(b"y" * 32)
    assert rotate_file(log, max_bytes=8, keep=2) is True
    assert (tmp_path / "crawler-cron.log.2").read_bytes() == b"x" * 32
    assert (tmp_path / "crawler-cron.log.1").read_bytes() == b"y" * 32


def test_cleanup_diagnostics_only_removes_old_regular_files(tmp_path):
    diagnostics = tmp_path / "diagnostics"
    diagnostics.mkdir()
    old = diagnostics / "old.json"
    fresh = diagnostics / "fresh.json"
    subdir = diagnostics / "keep-dir"
    old.write_text("old")
    fresh.write_text("fresh")
    subdir.mkdir()
    now = 1_800_000_000
    os.utime(old, (now - 20 * 86400, now - 20 * 86400))
    os.utime(fresh, (now - 2 * 86400, now - 2 * 86400))

    assert cleanup_diagnostics(diagnostics, max_age_days=14, now=now) == ["old.json"]
    assert not old.exists()
    assert fresh.exists()
    assert subdir.exists()


def test_run_maintenance_preserves_commercial_history_contract(tmp_path):
    result = run_maintenance(
        log_file=tmp_path / "missing.log",
        diagnostics_dir=tmp_path / "missing-diagnostics",
    )
    assert result == {
        "log_rotated": False,
        "diagnostics_removed": [],
        "commercial_history": "preserved",
    }


def test_cli_maintenance_does_not_initialize_database(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    with patch("dealhunter.cli.setup_db", side_effect=AssertionError("maintenance must not open SQLite")):
        main(["maintenance", "run"])
    output = capsys.readouterr().out
    assert '"commercial_history": "preserved"' in output
