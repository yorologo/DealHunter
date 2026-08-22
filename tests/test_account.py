"""Tests for the read-only account diagnostics."""

import os
import sys
from unittest.mock import patch, MagicMock
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.account import get_account_status
from dealhunter.errors import DealHunterError

def test_account_not_configured():
    config = {}
    with patch.dict(os.environ, clear=True):
        status = get_account_status(config, check_network=False)
    assert status["status"] == "NOT_CONFIGURED"

@patch('dealhunter.account.fetch_account_profile')
def test_account_status_valid(mock_fetch):
    mock_fetch.return_value = {"market": "MX", "prime": False}
    with patch.dict(os.environ, {"RAPPI_BEARER_TOKEN": "dummy"}):
        status = get_account_status({}, check_network=True)
    assert status["status"] == "VALID"
    assert status["market"] == "MX"
    assert "email" not in status

@patch('dealhunter.account.fetch_account_profile')
def test_account_status_invalid_session(mock_fetch):
    mock_fetch.side_effect = DealHunterError("ACCOUNT_SESSION_UNAVAILABLE", "Invalid", recoverable=False)
    with patch.dict(os.environ, {"RAPPI_BEARER_TOKEN": "expired"}):
        status = get_account_status({}, check_network=True)
    
    assert status["status"] == "EXPIRED"

@patch('dealhunter.api.urllib.request.urlopen')
def test_fetch_profile_401(mock_urlopen):
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

@patch('dealhunter.account.fetch_account_profile')
def test_account_status_unverified(mock_fetch):
    mock_fetch.return_value = "UNVERIFIED"
    from unittest.mock import patch
    import os
    with patch.dict(os.environ, {"RAPPI_BEARER_TOKEN": "dummy"}):
        status = get_account_status({}, check_network=True)
    assert status["status"] == "UNVERIFIED"

@patch('dealhunter.api.urllib.request.urlopen')
def test_fetch_profile_waf_fallback_unverified(mock_urlopen):
    from unittest.mock import MagicMock
    import json
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = json.dumps({"stores": [{"eta": ""}]}).encode('utf-8')
    mock_urlopen.return_value = mock_response
    
    from dealhunter.api import fetch_account_profile
    res = fetch_account_profile("dummy")
    assert res == "UNVERIFIED"

@patch('dealhunter.api.urllib.request.urlopen')
def test_fetch_profile_waf_fallback_valid(mock_urlopen):
    from unittest.mock import MagicMock
    import json
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = json.dumps({"stores": [{"eta": "8 - 11 min"}]}).encode('utf-8')
    mock_urlopen.return_value = mock_response
    
    from dealhunter.api import fetch_account_profile
    res = fetch_account_profile("dummy")
    assert isinstance(res, dict)
    assert res["note"] == "Validated via unified-search (eta present)"
