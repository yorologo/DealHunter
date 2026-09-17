import os
import json
import logging
from typing import Dict, Optional, Any
import urllib.request
import urllib.error

class AccessContext:
    def __init__(self, access_token: str, refresh_token: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self.metadata = metadata or {}

    def get_auth_headers(self) -> Dict[str, str]:
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}
        
    def __repr__(self):
        return "<AccessContext (Redacted)>"

class RappiSessionProvider:
    def __init__(self, storage_path: str = "~/.config/dealhunter/session.json"):
        self.storage_path = os.path.expanduser(storage_path)
        self.context: Optional[AccessContext] = None
        self._load()

    def _load(self):
        # Always try env var first for legacy/CI support
        env_token = os.environ.get("RAPPI_BEARER_TOKEN")
        if env_token:
            self.context = AccessContext(env_token)
            return

        try:
            from .secret_store import SecretStore
            store = SecretStore(config_dir=os.path.dirname(self.storage_path))
            token = store.load()
            if token:
                self.context = AccessContext(token)
        except Exception:
            pass

    def save(self, context: AccessContext):
        """Persist first, then expose the context; storage failures fail closed."""
        from .secret_store import SecretStore
        store = SecretStore(config_dir=os.path.dirname(self.storage_path))
        store.store(context._access_token)
        self.context = context
        return True

    async def is_authenticated(self) -> bool:
        return self.context is not None and bool(self.context._access_token)

    async def get_access_context(self) -> AccessContext:
        if not await self.is_authenticated():
            raise RuntimeError("AUTH_REQUIRED: No active session available.")
        return self.context

    async def invalidate(self) -> None:
        self.context = None
        try:
            from .secret_store import SecretStore
            SecretStore().delete()
        except Exception:
            pass
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)

class AuthenticatedHttpClient:
    def __init__(self, provider: RappiSessionProvider):
        self.provider = provider
        
    def _redact(self, text: str) -> str:
        if not text: return text
        if self.provider.context and self.provider.context._access_token:
            text = text.replace(self.provider.context._access_token, "eyJ...<REDACTED>")
        return text

    def request_sync(self, method: str, url: str, payload: Optional[Dict] = None, headers: Optional[Dict] = None, require_auth: bool = True) -> Any:
        context = self.provider.context if self.provider else None
        if require_auth and (not context or not context._access_token):
            raise RuntimeError("AUTH_REQUIRED: No active session available.")
        req_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DealHunter/3.0"
        }
        if context:
            req_headers.update(context.get_auth_headers())
        if headers:
            req_headers.update(headers)
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read().decode('utf-8')
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code in [401, 403]:
                raise RuntimeError(f"AUTH_EXPIRED or UNAUTHORIZED: HTTP {e.code}")
            if e.code == 429:
                raise RuntimeError("RATE_LIMIT: HTTP 429")
            raise RuntimeError(f"HTTP ERROR {e.code}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"NETWORK_ERROR: {e}")

    async def request(self, method: str, url: str, payload: Optional[Dict] = None, headers: Optional[Dict] = None) -> Any:
        # Synchronous urllib is intentional for this small Termux client; keep a
        # single auth/header/error contract for sync catalog discovery and async callers.
        return self.request_sync(method, url, payload=payload, headers=headers)


import http.server
import socketserver
import threading
import json
import urllib.parse
import secrets

def build_mobile_bookmarklet(callback_url: str, nonce: str) -> str:
    """Build the shared Rappi mobile bookmarklet for a loopback callback."""
    parsed = urllib.parse.urlsplit(callback_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("Mobile auth callback must use loopback HTTP")
    if parsed.query or parsed.fragment:
        raise ValueError("Mobile auth callback must not contain query or fragment")
    if not nonce:
        raise ValueError("Mobile auth nonce is required")

    callback_js = json.dumps(callback_url)
    nonce_js = json.dumps(str(nonce))
    script = f"""javascript:(function(){{
  if (window.location.hostname !== 'www.rappi.com.mx' && window.location.hostname !== 'rappi.com.mx') {{ alert('DealHunter: Solo en rappi.com.mx'); return; }}
  if (window.__dh_active) {{ alert('DealHunter: Interceptor activo. Busca algo (ej: coca cola).'); return; }}
  window.__dh_active = true;
  function onToken(t) {{
    if (typeof t !== 'string' || !t.startsWith('Bearer ')) return;
    const val = t.replace('Bearer ', '').trim();
    if (!val || window.__dh_found === val) return;
    window.__dh_found = val;
    const pay = JSON.stringify({{nonce: {nonce_js}, token: val}});
    window.location.href = {callback_js} + '#' + btoa(unescape(encodeURIComponent(pay)));
  }}
  const oF = window.fetch;
  window.fetch = async function(...args) {{
    try {{
      const opts = args[1] || {{}};
      if (opts.headers) {{
        let a = null;
        if (opts.headers instanceof Headers) a = opts.headers.get('Authorization');
        else if (Array.isArray(opts.headers)) {{ const h = opts.headers.find(x => x[0].toLowerCase() === 'authorization'); if (h) a = h[1]; }}
        else if (typeof opts.headers === 'object') {{ const k = Object.keys(opts.headers).find(k => k.toLowerCase() === 'authorization'); if (k) a = opts.headers[k]; }}
        if (a) onToken(a);
      }}
    }} catch(e) {{}}
    return oF.apply(this, args);
  }};
  const oO = XMLHttpRequest.prototype.open;
  const oS = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function() {{ return oO.apply(this, arguments); }};
  XMLHttpRequest.prototype.setRequestHeader = function(h, v) {{ if (h.toLowerCase() === 'authorization') onToken(v); return oS.apply(this, arguments); }};
  alert('DealHunter Interceptor activo. Haz una búsqueda en la página (ej: "coca cola") para capturar la sesión.');
}})();"""
    return script.replace("\\n", "")


class LocalAuthImporter:
    def __init__(self, provider: RappiSessionProvider, host="127.0.0.1", port=0, is_mobile=False, diagnose=False):
        self.provider = provider
        self.host = host
        self.port = port
        self.is_mobile = is_mobile
        self.diagnose = diagnose
        self.nonce = secrets.token_hex(16)
        self.success_event = threading.Event()
        self.server = None
        self.error_msg = None

    def start(self):
        outer = self
        
        class AuthHandler(http.server.SimpleHTTPRequestHandler):
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                
            def do_GET(self):
                if self.path.startswith('/diagnose') and outer.diagnose:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.end_headers()
                    html = """<!DOCTYPE html>
<html>
<head>
<title>DealHunter Diagnostic</title>
<style>
  body { font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }
  h1, h2, h3 { color: #569cd6; }
  .warning { background: #ffcc00; color: #000; padding: 10px; font-weight: bold; margin-bottom: 10px; }
  .candidate { border: 1px solid #4CAF50; padding: 10px; margin-bottom: 10px; }
  pre { white-space: pre-wrap; word-wrap: break-word; }
  button { padding: 10px; background: #007acc; color: #fff; border: none; cursor: pointer; }
  .raw-values { display: none; background: #2d2d2d; padding: 10px; border-left: 3px solid #ffcc00; }
</style>
</head>
<body>
<h1>=== DealHunter Rappi Authentication Diagnostic ===</h1>
<div id="summary">Loading...</div>
<div id="details"></div>
<script>
  const payloadStr = location.hash.substring(1);
  history.replaceState(null, '', location.pathname);
  if (!payloadStr) {
    document.getElementById('summary').innerText = "No payload found in hash.";
  } else {
    try {
      const rawJson = decodeURIComponent(escape(atob(payloadStr)));
      const report = JSON.parse(rawJson);
      
      let jwtCandidates = 0;
      let sessionCookies = 0;
      
      const candidatesHtml = [];
      const rawHtml = [];
      
      function processEntry(source, key, entry) {
        if (entry.type === 'JWT') {
          jwtCandidates++;
          let cls = 'UNKNOWN_AUTH_MATERIAL';
          if (entry.jwt && entry.jwt.payload) {
             if (entry.jwt.payload.exp) cls = 'LIKELY_ACCESS_TOKEN';
          }
          candidatesHtml.push(`<div class="candidate">
            <strong>Source:</strong> ${source}["${key}"]<br>
            <strong>Type:</strong> JWT<br>
            <strong>Classification:</strong> ${cls}<br>
            <strong>Header:</strong> ${JSON.stringify(entry.jwt?.header || {})}
          </div>`);
          rawHtml.push(`<div><strong>${source}["${key}"]</strong>:<br><pre>${entry.raw}</pre></div><hr>`);
        } else if (entry.nested && entry.nested.length > 0) {
          entry.nested.forEach(n => {
            jwtCandidates++;
            let cls = 'LIKELY_ACCESS_TOKEN';
            candidatesHtml.push(`<div class="candidate">
              <strong>Source:</strong> ${source}["${key}"] -> ${n.path}<br>
              <strong>Type:</strong> JWT_EMBEDDED<br>
              <strong>Classification:</strong> ${cls}<br>
              <strong>Header:</strong> ${JSON.stringify(n.jwt?.header || {})}
            </div>`);
            rawHtml.push(`<div><strong>${source}["${key}"] -> ${n.path}</strong>:<br><pre>${n.raw}</pre></div><hr>`);
          });
        }
      }

      report.localStorage.forEach(e => processEntry('localStorage', e.key, e));
      report.sessionStorage.forEach(e => processEntry('sessionStorage', e.key, e));
      report.cookies.forEach(e => {
        sessionCookies++;
        processEntry('cookie', e.key, e);
      });
      
      const idbs = Array.isArray(report.indexedDB) ? report.indexedDB.map(db => db.name + " (" + db.stores.join(',') + ")").join(' | ') : report.indexedDB;
      
      const summary = `
        <p>Origin: ${report.origin}</p>
        <p>localStorage entries: ${report.localStorage.length}</p>
        <p>sessionStorage entries: ${report.sessionStorage.length}</p>
        <p>Visible cookie names: ${report.cookies.map(c=>c.key).join(', ')}</p>
        <p>IndexedDB databases: ${idbs}</p>
        <hr>
        <p><strong>JWT candidates: ${jwtCandidates}</strong></p>
      `;
      
      document.getElementById('summary').innerHTML = summary;
      
      let details = `<h2>Candidates</h2>${candidatesHtml.join('')}`;
      details += `<button onclick="document.getElementById('raw').style.display='block'">Show raw values</button>`;
      details += `<div id="raw" class="raw-values">
        <div class="warning">LOCAL DIAGNOSTIC ONLY — DO NOT SHARE THIS OUTPUT</div>
        ${rawHtml.join('')}
      </div>`;
      
      document.getElementById('details').innerHTML = details;
      
      fetch('/diagnose_ack', {method: 'POST'}).catch(e=>{});
    } catch(e) {
      document.getElementById('summary').innerText = "Error parsing report: " + e;
    }
  }
</script>
</body>
</html>"""
                    self.wfile.write(html.encode('utf-8'))
                elif self.path.startswith('/import') and outer.is_mobile and not outer.diagnose:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.end_headers()
                    html = """<!DOCTYPE html>
<html>
<head><title>DH Import</title></head>
<body>
<script>
  const payload = location.hash.substring(1);
  history.replaceState(null, '', location.pathname);
  if (!payload) {
    document.body.innerText = "Error: No payload found.";
  } else {
    document.body.innerText = "Importing session securely...";
    fetch('/commit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: atob(payload)
    }).then(r => r.json()).then(data => {
      document.body.innerText = data.status === 'ok' ? 'DealHunter Auth OK! You can close this tab and return to Termux.' : 'DealHunter Auth Failed: ' + data.error;
    }).catch(e => {
      document.body.innerText = 'Error: ' + e;
    });
  }
</script>
</body>
</html>"""
                    self.wfile.write(html.encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == '/diagnose_ack' and outer.diagnose:
                    self.send_response(200)
                    self.end_headers()
                    print("\n[+] Diagnostic report generated in browser.")
                    outer.success_event.set()
                    threading.Thread(target=self.server.shutdown).start()
                    return
                    
                if self.path == '/commit' or (not outer.is_mobile and self.path == '/'):
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 1024000: # Max 1MB
                        self._reject("Payload too large")
                        return

                    post_data = self.rfile.read(content_length)
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        received_nonce = data.get("nonce")
                        if not outer.nonce or received_nonce != outer.nonce:
                            self._reject("Invalid nonce")
                            return
                        tokens = data.get("tokens", [])
                        if "token" in data: tokens.append(data["token"])
                        
                        best_token = None
                        if tokens: best_token = tokens[0]
                        else:
                            self._reject("No tokens provided")
                            return
                        
                        print(f"[+] Received verified token from God-Mode scanner!")
                        if outer.provider:
                            outer.provider.save(AccessContext(best_token))
                        outer.nonce = None # Invalidate nonce
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b'{"status": "ok"}')
                        print("\n[+] Session imported securely")
                        
                        outer.success_event.set()
                        threading.Thread(target=self.server.shutdown).start()
                        return
                    except Exception as e:
                        self._reject(f"Error parsing token")
                else:
                    self.send_response(404)
                    self.end_headers()

            def _reject(self, msg):
                outer.error_msg = msg
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": msg}).encode('utf-8'))
                print(f"\n[!] {msg}")

            def log_message(self, format, *args):
                pass
                
        self.server = socketserver.TCPServer((self.host, self.port), AuthHandler)
        self.port = self.server.server_address[1]

    def serve_with_timeout(self, timeout=300):
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        success = self.success_event.wait(timeout)
        self.server.shutdown()
        self.server.server_close()
        
        # Invalidate nonce
        self.nonce = None
        return success
