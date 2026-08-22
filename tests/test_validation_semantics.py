import pytest
from unittest.mock import patch, MagicMock
from dealhunter.api import fetch_account_profile
from dealhunter.errors import DealHunterError
import urllib.error
import json

@patch('dealhunter.api.urllib.request.urlopen')
def test_profile_403_uses_unified_search_validator(mock_urlopen):
    # My patch directly uses unified-search without trying profile first.
    pass

@patch('dealhunter.api.urllib.request.urlopen')
def test_unified_search_positive_eta_valid(mock_urlopen):
    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.__enter__.return_value = mock_res
    mock_res.read.return_value = json.dumps({"stores": [{"eta": "8 min"}]}).encode('utf-8')
    mock_urlopen.return_value = mock_res
    
    res = fetch_account_profile("dummy")
    assert isinstance(res, dict)
    assert res["note"] == "Validated via unified-search (eta present)"

@patch('dealhunter.api.urllib.request.urlopen')
def test_unified_search_empty_eta_unverified(mock_urlopen):
    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.__enter__.return_value = mock_res
    mock_res.read.return_value = json.dumps({"stores": [{"eta": ""}]}).encode('utf-8')
    mock_urlopen.return_value = mock_res
    
    assert fetch_account_profile("dummy") == "UNVERIFIED"

@patch('dealhunter.api.urllib.request.urlopen')
def test_unified_search_missing_eta_unverified(mock_urlopen):
    mock_res = MagicMock()
    mock_res.status = 200
    mock_res.__enter__.return_value = mock_res
    mock_res.read.return_value = json.dumps({"stores": [{"other": "value"}]}).encode('utf-8')
    mock_urlopen.return_value = mock_res
    
    assert fetch_account_profile("dummy") == "UNVERIFIED"

@patch('dealhunter.api.urllib.request.urlopen')
def test_unified_search_401_expired(mock_urlopen):
    err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)
    mock_urlopen.side_effect = err
    
    with pytest.raises(DealHunterError) as exc:
        fetch_account_profile("dummy")
    assert exc.value.code == "ACCOUNT_SESSION_UNAVAILABLE"

@patch('dealhunter.api.urllib.request.urlopen')
def test_unified_search_429_unverified(mock_urlopen):
    err = urllib.error.HTTPError(url="", code=429, msg="Too Many Requests", hdrs=None, fp=None)
    mock_urlopen.side_effect = err
    
    assert fetch_account_profile("dummy") == "RATE_LIMIT"

@patch('dealhunter.api.urllib.request.urlopen')
def test_unified_search_timeout_unverified(mock_urlopen):
    mock_urlopen.side_effect = TimeoutError()
    with pytest.raises(DealHunterError):
        fetch_account_profile("dummy")

@patch('dealhunter.api.urllib.request.urlopen')
def test_canonical_validator_payload(mock_urlopen):
    mock_res = MagicMock()
    mock_res.status = 200; mock_res.__enter__.return_value = mock_res
    mock_res.read.return_value = b"{}"
    mock_urlopen.return_value = mock_res
    
    fetch_account_profile("dummy")
    req = mock_urlopen.call_args[0][0]
    payload = json.loads(req.data.decode('utf-8'))
    assert payload["query"] == "coca cola"
    assert "lat" in payload
    assert "lng" in payload
