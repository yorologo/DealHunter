"""Tests for the read-only account diagnostics."""

import os
import sys
from unittest.mock import patch, MagicMock
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.account import get_account_status, sanitize_account_data
from dealhunter.errors import DealHunterError

def test_account_not_configured():
    config = {}
    with patch.dict(os.environ, clear=True):
        status = get_account_status(config)
    assert status["status"] == "NOT_CONFIGURED"

def test_account_sanitization():
    raw_data = {
        "email": "user@example.com",
        "phone": "+521111111111",
        "first_name": "John",
        "last_name": "Doe",
        "market": "MX",
        "region": "CDMX",
        "prime": True,
        "prime_type": "Pro",
        "benefits": {
            "promotions": [{"id": 1}, {"id": 2}]
        },
        "device_id": "secret-device-id",
        "tokens": {"auth": "bearer xyz"}
    }
    
    safe = sanitize_account_data(raw_data)
    
    assert "email" not in safe
    assert "phone" not in safe
    assert "first_name" not in safe
    assert "tokens" not in safe
    assert "device_id" not in safe
    
    assert safe["status"] == "VALID"
    assert safe["market"] == "MX"
    assert safe["has_prime"] is True
    assert safe["active_promos"] == 2

@patch('dealhunter.account.fetch_account_profile')
def test_account_status_valid(mock_fetch):
    mock_fetch.return_value = {"market": "MX", "prime": False}
    with patch.dict(os.environ, {"RAPPI_BEARER_TOKEN": "dummy"}):
        status = get_account_status({})
    assert status["status"] == "VALID"
    assert status["market"] == "MX"

@patch('dealhunter.account.fetch_account_profile')
def test_account_status_invalid_session(mock_fetch):
    mock_fetch.side_effect = DealHunterError("ACCOUNT_SESSION_UNAVAILABLE", "Invalid", recoverable=False)
    with patch.dict(os.environ, {"RAPPI_BEARER_TOKEN": "expired"}):
        status = get_account_status({})
    
    assert status["status"] == "UNAVAILABLE"
    assert "ACCOUNT_SESSION_UNAVAILABLE" in status["error"]

@patch('dealhunter.api.urllib.request.urlopen')
def test_fetch_profile_401(mock_urlopen):
    # Setup mock to raise HTTPError 401
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="", code=401, msg="Unauthorized", hdrs=None, fp=None
    )
    
    from dealhunter.api import fetch_account_profile
    try:
        fetch_account_profile("bad_token")
        assert False, "Should have raised DealHunterError"
    except DealHunterError as e:
        assert e.code == "ACCOUNT_SESSION_UNAVAILABLE"

def test_token_cannot_be_saved_in_config():
    from dealhunter.cli import handle_config_command
    import argparse
    args = argparse.Namespace(action="set", key="rappi_token", value="secret")
    try:
        handle_config_command(args)
        assert False, "Should have exited"
    except SystemExit:
        pass
    
    from dealhunter.config import load_config
    cfg = load_config()
    assert "rappi_token" not in cfg

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nAccount tests: {passed} total, {passed} passed, 0 failed.")
