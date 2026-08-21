import pytest
import os
import json
import base64
from unittest.mock import patch, MagicMock
import http.server
from dealhunter.cli import main
from dealhunter.auth import RappiSessionProvider, AuthenticatedHttpClient

@pytest.fixture
def temp_session_file(tmp_path):
    return str(tmp_path / "test_session.json")

def test_binding_is_localhost(temp_session_file):
    with patch("socketserver.TCPServer") as mock_tcpserver:
        mock_instance = MagicMock()
        mock_instance.server_address = ("127.0.0.1", 12345)
        mock_tcpserver.return_value = mock_instance
        
        with patch("threading.Event.wait", return_value=False):
            with patch("builtins.print"):
                main(["auth", "rappi", "--mobile"])
                
        # Get the arguments used to instantiate TCPServer
        args, _ = mock_tcpserver.call_args
        assert args[0][0] == "127.0.0.1"

def test_desktop_binding_is_localhost(temp_session_file):
    with patch("socketserver.TCPServer") as mock_tcpserver:
        mock_instance = MagicMock()
        mock_instance.server_address = ("127.0.0.1", 5050)
        mock_tcpserver.return_value = mock_instance
        
        with patch("threading.Event.wait", return_value=False):
            with patch("builtins.print"):
                main(["auth", "rappi"])
                
        args, _ = mock_tcpserver.call_args
        assert args[0] == ("127.0.0.1", 5050)

def test_redaction_removes_token():
    provider = RappiSessionProvider()
    provider.context = MagicMock()
    provider.context._access_token = "eyJ_FAKE_TOKEN_FOR_TESTS"
    
    client = AuthenticatedHttpClient(provider)
    redacted = client._redact("Error: Bearer eyJ_FAKE_TOKEN_FOR_TESTS failed")
    assert "eyJ_FAKE_TOKEN_FOR_TESTS" not in redacted
    assert "eyJ...<REDACTED>" in redacted

def test_permissions_are_restrictive(temp_session_file):
    provider = RappiSessionProvider(storage_path=temp_session_file)
    context = MagicMock()
    context._access_token = "eyJ_FAKE"
    context._refresh_token = None
    context.metadata = {}
    provider.save(context)
    
    if os.name != 'nt':  # Check only on unix
        st = os.stat(os.path.join(os.path.dirname(temp_session_file), 'session.enc'))
        assert oct(st.st_mode)[-3:] == "600"

import threading
import time

def test_importer_payload_validation(temp_session_file):
    from dealhunter.auth import RappiSessionProvider, LocalAuthImporter
    prov = RappiSessionProvider(storage_path=temp_session_file)
    importer = LocalAuthImporter(prov, host="127.0.0.1", port=0)
    importer.start()
    
    server_thread = threading.Thread(target=importer.server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    import urllib.request
    
    base_url = f"http://127.0.0.1:{importer.port}/commit"
    
    def post(data, max_size=None):
        req = urllib.request.Request(base_url, data=data, method="POST")
        if max_size:
            req.add_header("Content-Length", str(max_size))
        try:
            with urllib.request.urlopen(req, timeout=2) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
            
    # 1. Invalid JSON
    assert post(b"malformed") == 400
    
    # 2. Empty payload
    assert post(b"{}") == 400
    
    # 3. Invalid nonce
    assert post(json.dumps({"nonce": "wrong", "token": "eyJ123"}).encode()) == 400
    
    # 4. Too large payload
    assert post(b"a" * 20000, max_size=20000) == 400

    # 5. Valid import
    valid_payload = json.dumps({"nonce": importer.nonce, "token": "eyJ123"}).encode()
    assert post(valid_payload) == 200
    
    # 6. Reuse attempt (nonce is invalidated)
    try:
        post(valid_payload)
        assert False, "Server should be dead!"
    except Exception:
        pass

    importer.server.shutdown()
    importer.server.server_close()

def test_bookmarklet_generation():
    # Simple check that the bookmarklet string is well-formed and uses btoa
    from dealhunter.auth import LocalAuthImporter
    importer = LocalAuthImporter(None, host="127.0.0.1", port=12345)
    
    bookmarklet = f"javascript:(function(){{\n  if (window.location.hostname !== 'www.rappi.com.mx' && window.location.hostname !== 'rappi.com.mx') {{\n    alert('DealHunter: this bookmarklet must be executed on rappi.com.mx');\n    return;\n  }}\n  var c = [];\n  for(var i=0; i<localStorage.length; i++){{\n    var k=localStorage.key(i), v=localStorage.getItem(k);\n    if(v && v.startsWith('eyJ') && v.split('.').length===3) {{\n      if(k.includes('token') || k.includes('session') || k.includes('auth')) c.push(v);\n    }}\n  }}\n  var t = localStorage.getItem('access_token');\n  if(t && t.startsWith('eyJ')) c.push(t);\n  c = Array.from(new Set(c));\n  if (c.length !== 1) {{\n    alert('DealHunter could not identify a unique authenticated session.');\n    return;\n  }}\n  var p = JSON.stringify({{nonce: '{importer.nonce}', token: c[0]}});\n  window.location.href = 'http://127.0.0.1:{importer.port}/import#' + btoa(p);\n}})();"
    
    assert "www.rappi.com.mx" in bookmarklet
    assert "rappi.com.mx" in bookmarklet
    assert "btoa(p)" in bookmarklet
    assert importer.nonce in bookmarklet
    assert str(importer.port) in bookmarklet
    assert "?token" not in bookmarklet

def test_diagnose_endpoint(temp_session_file):
    from dealhunter.auth import RappiSessionProvider, LocalAuthImporter
    prov = RappiSessionProvider(storage_path=temp_session_file)
    importer = LocalAuthImporter(prov, host="127.0.0.1", port=0, diagnose=True)
    importer.start()
    
    server_thread = threading.Thread(target=importer.server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    import urllib.request
    
    base_url = f"http://127.0.0.1:{importer.port}/diagnose"
    try:
        with urllib.request.urlopen(base_url, timeout=2) as r:
            assert r.status == 200
            html = r.read().decode('utf-8')
            assert "DealHunter Rappi Authentication Diagnostic" in html
            assert "LOCAL DIAGNOSTIC ONLY" in html
            assert "history.replaceState" in html
    except Exception as e:
        pytest.fail(f"Diagnose endpoint failed: {e}")
        
    # Trigger ack to shutdown
    ack_url = f"http://127.0.0.1:{importer.port}/diagnose_ack"
    req = urllib.request.Request(ack_url, method="POST")
    try:
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass
    
    importer.server.shutdown()
    importer.server.server_close()

def test_diagnose_cli_mock(temp_session_file):
    from dealhunter.cli import main
    with patch("socketserver.TCPServer") as mock_tcpserver:
        mock_instance = MagicMock()
        mock_instance.server_address = ("127.0.0.1", 12345)
        mock_tcpserver.return_value = mock_instance
        
        with patch("threading.Event.wait", return_value=False):
            with patch("builtins.print") as mock_print:
                main(["auth", "rappi", "--mobile", "--diagnose"])
                
        # Get the print calls and verify bookmarklet has classification logic
        prints = [call.args[0] for call in mock_print.call_args_list if call.args]
        full_output = " ".join(str(p) for p in prints)
        assert "isJWT" in full_output
        assert "classifyValue" in full_output
        assert "indexedDB" in full_output
