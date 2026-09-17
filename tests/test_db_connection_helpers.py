import sqlite3
import pytest
from dealhunter.db import read_connection, write_connection, setup_db


def test_read_connection_is_filesystem_read_only(tmp_path):
    db = tmp_path / 'db.sqlite'
    setup_db(str(db)).close()
    with read_connection(str(db)) as conn:
        assert conn.execute('SELECT version FROM schema_version').fetchone()[0] >= 1
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO runs(run_id,status) VALUES('x','SUCCESS')")


def test_read_connection_missing_file_does_not_create_it(tmp_path):
    db = tmp_path / 'missing.sqlite'
    with pytest.raises(sqlite3.OperationalError):
        with read_connection(str(db)):
            pass
    assert not db.exists()


def test_write_connection_commits_and_rolls_back(tmp_path):
    db = tmp_path / 'db.sqlite'
    setup_db(str(db)).close()
    with write_connection(str(db)) as conn:
        conn.execute("INSERT INTO runs(run_id,status) VALUES('ok','SUCCESS')")
    with read_connection(str(db)) as conn:
        assert conn.execute("SELECT status FROM runs WHERE run_id='ok'").fetchone()[0] == 'SUCCESS'
    with pytest.raises(RuntimeError):
        with write_connection(str(db)) as conn:
            conn.execute("INSERT INTO runs(run_id,status) VALUES('rollback','SUCCESS')")
            raise RuntimeError('boom')
    with read_connection(str(db)) as conn:
        assert conn.execute("SELECT 1 FROM runs WHERE run_id='rollback'").fetchone() is None


def test_watchlist_db_error_is_not_reported_as_empty(tmp_path):
    from dealhunter.web.queries import get_watchlist
    db = tmp_path / 'not-dealhunter.sqlite'
    sqlite3.connect(db).close()
    with pytest.raises(sqlite3.OperationalError):
        get_watchlist(str(db))


def test_admin_home_surfaces_data_errors(tmp_path, monkeypatch):
    from dealhunter.web.app import create_app
    import dealhunter.web.admin as admin
    db = tmp_path / 'db.sqlite'
    setup_db(str(db)).close()
    monkeypatch.setattr(admin, 'get_run_status_summary', lambda *_: (_ for _ in ()).throw(sqlite3.OperationalError('runs unavailable')))
    monkeypatch.setattr(admin, 'db_status', lambda *_: (_ for _ in ()).throw(sqlite3.OperationalError('stats unavailable')))
    monkeypatch.setattr(admin, 'run_doctor', lambda **_: (_ for _ in ()).throw(sqlite3.OperationalError('doctor unavailable')))
    app = create_app({'DATABASE': str(db), 'TESTING': True, 'SECRET_KEY': 'test'})
    rv = app.test_client().get('/admin/')
    assert rv.status_code == 200
    text = rv.get_data(as_text=True)
    assert 'No se pudieron leer todos los datos del sistema' in text
    assert 'runs unavailable' in text
    assert 'stats unavailable' in text


def test_catalog_sync_db_error_is_not_zero_data(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from dealhunter.web.app import create_app
    import dealhunter.web.admin as admin
    db = tmp_path / 'db.sqlite'
    setup_db(str(db)).close()
    @contextmanager
    def bad_read(*_args, **_kwargs):
        raise sqlite3.OperationalError('storage unavailable')
        yield
    monkeypatch.setattr(admin, 'read_connection', bad_read)
    app = create_app({'DATABASE': str(db), 'TESTING': True, 'SECRET_KEY': 'test'})
    rv = app.test_client().get('/admin/catalog-sync')
    assert rv.status_code == 200
    text = rv.get_data(as_text=True)
    assert 'Error de base de datos' in text
    assert 'storage unavailable' in text
    assert 'No disponible' in text
