import pytest
import asyncio
from unittest.mock import patch, MagicMock
from dealhunter.auth import AccessContext, RappiSessionProvider, AuthenticatedHttpClient
import urllib.error

def test_token_redaction():
    provider = RappiSessionProvider()
    provider.context = AccessContext("eyJ_SECRET_TOKEN_HERE")
    client = AuthenticatedHttpClient(provider)
    
    dirty_string = "Log message: Bearer eyJ_SECRET_TOKEN_HERE"
    clean_string = client._redact(dirty_string)
    
    assert "eyJ_SECRET_TOKEN_HERE" not in clean_string
    assert "eyJ...<REDACTED>" in clean_string

def test_auth_expired():
    async def run_test():
        provider = RappiSessionProvider()
        provider.context = AccessContext("expired_token")
        client = AuthenticatedHttpClient(provider)
        
        mock_error = urllib.error.HTTPError("http://test", 401, "Unauthorized", {}, None)
        
        with patch("urllib.request.urlopen", side_effect=mock_error):
            try:
                await client.request("GET", "http://test")
                assert False, "Should have raised exception"
            except RuntimeError as e:
                assert "AUTH_EXPIRED or UNAUTHORIZED" in str(e)
    
    asyncio.run(run_test())


def test_optional_auth_request_allows_anonymous():
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"ok": true}'
    client = AuthenticatedHttpClient(None)
    with patch("urllib.request.urlopen", return_value=Response()) as mocked:
        assert client.request_sync("GET", "http://test", require_auth=False) == {"ok": True}
    request = mocked.call_args.args[0]
    assert request.get_header("Authorization") is None


def test_optional_auth_request_keeps_bearer_when_present():
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"ok": true}'
    provider = RappiSessionProvider()
    provider.context = AccessContext("TEST_TOKEN")
    client = AuthenticatedHttpClient(provider)
    with patch("urllib.request.urlopen", return_value=Response()) as mocked:
        assert client.request_sync("GET", "http://test", require_auth=False) == {"ok": True}
    request = mocked.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer TEST_TOKEN"
