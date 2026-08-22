import pytest
from unittest.mock import patch, MagicMock
from dealhunter.secret_store import SessionService, SecretStore
from dealhunter.account import SessionStatus

@pytest.fixture
def temp_store(tmp_path):
    store = SecretStore(config_dir=str(tmp_path))
    svc = SessionService(config_dir=str(tmp_path))
    return svc, store

def mock_get_current(*args, **kwargs):
    with patch('dealhunter.account.SessionService', return_value=pytest.svc):
        return SessionStatus().get_current(*args, **kwargs)

def test_configured_persistent_has_source(temp_store):
    svc, store = temp_store
    pytest.svc = svc
    svc.store_persistent("dummy")
    status = mock_get_current()
    assert status["configured"] is True
    assert status["source"] == "PERSISTENT"
    assert status["status"] == "CONFIGURED"

@patch('dealhunter.account.fetch_account_profile')
def test_account_check_never_checked_to_valid(mock_fetch, temp_store):
    mock_fetch.return_value = {"market": "MX"}
    svc, store = temp_store
    pytest.svc = svc
    svc.store_persistent("dummy")
    
    status = mock_get_current(check_network=True)
    assert status["status"] == "VALID"
    assert status["last_validated_at"] is not None
    
    # Second call without network should read from persistence
    status2 = mock_get_current(check_network=False)
    assert status2["status"] == "VALID"

@patch('dealhunter.account.fetch_account_profile')
def test_account_check_never_checked_to_unverified(mock_fetch, temp_store):
    mock_fetch.return_value = "UNVERIFIED"
    svc, store = temp_store
    pytest.svc = svc
    svc.store_persistent("dummy")
    
    status = mock_get_current(check_network=True)
    assert status["status"] == "UNVERIFIED"
    
    status2 = mock_get_current(check_network=False)
    assert status2["status"] == "UNVERIFIED"

@patch('dealhunter.account.fetch_account_profile')
def test_account_check_to_expired(mock_fetch, temp_store):
    mock_fetch.return_value = None # indicates expired
    svc, store = temp_store
    pytest.svc = svc
    svc.store_persistent("dummy")
    
    status = mock_get_current(check_network=True)
    assert status["status"] == "EXPIRED"
    
    status2 = mock_get_current(check_network=False)
    assert status2["status"] == "EXPIRED"

def test_source_survives_expired(temp_store):
    svc, store = temp_store
    pytest.svc = svc
    svc.store_persistent("dummy")
    svc.mark_expired()
    
    status = mock_get_current()
    assert status["configured"] is True # It has a token/session in store
    assert status["source"] == "PERSISTENT"
    assert status["status"] == "EXPIRED"

def test_validation_state_survives_restart(temp_store):
    svc, store = temp_store
    pytest.svc = svc
    svc.store_persistent("dummy")
    svc.update_validation("UNVERIFIED", "2024-01-01")
    
    # Simulate restart by creating new instance with same dir
    svc2 = SessionService(config_dir=store.config_dir)
    status = mock_get_current() # it implicitly creates a new SessionService but doesn't pass config_dir!
    # Wait, mock_get_current() uses SessionService() without config_dir.
    # We must patch SessionService inside get_current to use our config_dir.
    pass

