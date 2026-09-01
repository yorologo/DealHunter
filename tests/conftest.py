import pytest
import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def _file_digest(path):
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def guard_real_user_config():
    """Fail the suite if it creates or changes the user's real config file."""
    home = os.environ.get("HOME")
    if not home:
        yield
        return

    config_path = Path(home) / ".config" / "dealhunter" / "config.toml"
    before = _file_digest(config_path)
    yield
    assert _file_digest(config_path) == before, (
        f"Test suite modified the real DealHunter config: {config_path}"
    )

@pytest.fixture(autouse=True)
def isolate_config_and_env(tmp_path, monkeypatch):
    """Ensure no test reads the user's real config or environment variables."""
    # Isolate environment variables
    monkeypatch.delenv("RAPPI_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("RAPPI_DB_PATH", str(tmp_path / "default.db"))
    
    # Isolate config directory for SecretStore
    # Patch os.path.expanduser so '~' resolves to tmp_path
    original_expanduser = os.path.expanduser
    def mock_expanduser(path):
        if path.startswith('~'):
            return path.replace('~', str(tmp_path), 1)
        return original_expanduser(path)
        
    with patch('os.path.expanduser', side_effect=mock_expanduser):
        yield

from tests.helpers.db import create_current_schema_db

@pytest.fixture
def current_schema_db(tmp_path):
    """Provides an isolated connection to a fresh DB initialized with the current canonical schema."""
    db_file = tmp_path / "dealhunter_test.db"
    conn = create_current_schema_db(str(db_file))
    yield conn
    conn.close()
@pytest.fixture
def current_schema_db_path(tmp_path):
    """Provides the file path to a fresh DB initialized with the current canonical schema."""
    db_file = str(tmp_path / "dealhunter_test.db")
    conn = create_current_schema_db(db_file)
    conn.close()
    return db_file
