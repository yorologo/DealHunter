import pytest
import os
import tempfile
from unittest.mock import patch

@pytest.fixture(autouse=True)
def isolate_config_and_env(tmp_path, monkeypatch):
    """Ensure no test reads the user's real config or environment variables."""
    # Isolate environment variables
    monkeypatch.delenv("RAPPI_BEARER_TOKEN", raising=False)
    
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
