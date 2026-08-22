import sqlite3

import pytest

from dealhunter import cli


def _isolated_environment(monkeypatch, tmp_path):
    db_path = tmp_path / "location.db"
    monkeypatch.setenv("RAPPI_DB_PATH", str(db_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr("dealhunter.crawler.run_discover", lambda *args, **kwargs: ("COMPLETED", 0))
    monkeypatch.setattr('dealhunter.auth.RappiSessionProvider.is_authenticated', __import__('unittest.mock').mock.AsyncMock(return_value=False))
    return db_path


def test_crawl_requires_explicit_location(monkeypatch, tmp_path):
    db_path = _isolated_environment(monkeypatch, tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main(["discover"])

    assert exc.value.code == 2
    assert not db_path.exists()


def test_capture_provenance_is_stored_at_run_level(monkeypatch, tmp_path):
    db_path = _isolated_environment(monkeypatch, tmp_path)

    cli.main(["discover", "--lat", "19.5", "--lng", "-99.2"])

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT lat, lng FROM runs").fetchone() == (19.5, -99.2)


def test_location_change_warns_and_preserves_history(
    monkeypatch, tmp_path, capsys
):
    db_path = _isolated_environment(monkeypatch, tmp_path)
    cli.main(["discover", "--lat", "19.5", "--lng", "-99.2"])

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO observations
               (run_id, store_id, product_id, price, timestamp)
               SELECT run_id, 'store-1', 'product-1', 10, CURRENT_TIMESTAMP
               FROM runs LIMIT 1"""
        )
        conn.commit()

    cli.main(["discover", "--lat", "20.5", "--lng", "-100.2"])

    captured = capsys.readouterr()
    assert "LOCATION_CONTEXT_CHANGED" in captured.err
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 2
