"""
Uber Eats Browser Transport — CDP-based catalog acquisition.

Uses Chrome DevTools Protocol to observe and replay Uber Eats API calls
from within a legitimate browser session. No secrets are extracted;
the browser handles all authentication internally.

Architecture:
    DealHunter (Termux)
        → CDP WebSocket (127.0.0.1:9222 via SSH tunnel)
            → Chrome (Windows, dedicated profile)
                → ubereats.com (user's real session)

The transport:
    1. Connects to Chrome via CDP
    2. Installs a minimal XHR interceptor to capture CSRF token in-browser
    3. Uses Runtime.evaluate to call fetch() from the page context
    4. The browser supplies its own cookies/CSRF automatically
    5. Returns structured JSON responses to Python
    6. Never extracts cookies, tokens, or credentials
"""
import asyncio
import json
import logging
import time
import urllib.request

try:
    import websockets
except ImportError:
    websockets = None

logger = logging.getLogger(__name__)

# Health states
READY = "READY"
BROWSER_NOT_RUNNING = "BROWSER_NOT_RUNNING"
UBER_NOT_OPEN = "UBER_NOT_OPEN"
LOGIN_REQUIRED = "LOGIN_REQUIRED"
CHALLENGE_REQUIRED = "CHALLENGE_REQUIRED"
DISCONNECTED = "DISCONNECTED"
CAPTURE_TIMEOUT = "CAPTURE_TIMEOUT"
INVALID_RESPONSE = "INVALID_RESPONSE"
CSRF_NOT_AVAILABLE = "CSRF_NOT_AVAILABLE"

# Timeouts
CONNECT_TIMEOUT = 5
NAVIGATION_TIMEOUT = 15
FETCH_TIMEOUT = 15
RECV_TIMEOUT = 1.0

# Pacing
INTER_PAGE_DELAY = 1.5
INTER_STORE_DELAY = 3.0

# Max websocket frame size (Soriana catalog can be ~440KB)
MAX_WS_SIZE = 20_000_000


class UberBrowserTransport:
    """CDP-based transport for acquiring Uber Eats store catalogs."""

    def __init__(self, cdp_host="127.0.0.1", cdp_port=9222):
        if websockets is None:
            raise ImportError(
                "websockets package required for UberBrowserTransport. "
                "Install with: pip install websockets"
            )
        self.cdp_host = cdp_host
        self.cdp_port = cdp_port
        self._ws = None
        self._msg_id = 0
        self._csrf_installed = False

    def _next_id(self):
        self._msg_id += 1
        return self._msg_id

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self):
        """Check CDP connectivity. Returns a health state string."""
        try:
            url = f"http://{self.cdp_host}:{self.cdp_port}/json/version"
            req = urllib.request.urlopen(url, timeout=CONNECT_TIMEOUT)
            if req.status == 200:
                info = json.loads(req.read())
                logger.debug("CDP connected: %s", info.get("Browser"))
                return READY
        except Exception as e:
            logger.debug("CDP health check failed: %s", e)
        return BROWSER_NOT_RUNNING

    def get_browser_info(self):
        """Return sanitized browser info (no secrets)."""
        try:
            url = f"http://{self.cdp_host}:{self.cdp_port}/json/version"
            req = urllib.request.urlopen(url, timeout=CONNECT_TIMEOUT)
            info = json.loads(req.read())
            return {
                "browser": info.get("Browser"),
                "protocol_version": info.get("Protocol-Version"),
            }
        except Exception:
            return None

    def _get_tabs(self):
        """Return list of browser tabs."""
        try:
            url = f"http://{self.cdp_host}:{self.cdp_port}/json"
            req = urllib.request.urlopen(url, timeout=CONNECT_TIMEOUT)
            return json.loads(req.read())
        except Exception:
            return []

    def _find_uber_tab(self):
        """Find an Uber Eats page tab, or the first available page."""
        tabs = self._get_tabs()
        # Prefer an existing Uber tab
        for tab in tabs:
            if tab.get("type") == "page":
                tab_url = tab.get("url", "")
                if "ubereats.com" in tab_url or "uber.com/mx" in tab_url:
                    return tab.get("webSocketDebuggerUrl")
        # Fall back to first page tab
        for tab in tabs:
            if tab.get("type") == "page":
                return tab.get("webSocketDebuggerUrl")
        return None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self):
        """Connect to the browser via global CDP and create a dedicated target."""
        req = urllib.request.urlopen(f"http://{self.cdp_host}:{self.cdp_port}/json/version", timeout=CONNECT_TIMEOUT)
        version_info = json.loads(req.read())
        browser_ws_url = version_info["webSocketDebuggerUrl"]
        
        self._browser_ws = await websockets.connect(browser_ws_url, max_size=MAX_WS_SIZE)
        
        # Create target
        res = await self._send_global("Target.createTarget", {"url": "about:blank"})
        self._target_id = res["targetId"]
        
        # Attach to target
        res = await self._send_global("Target.attachToTarget", {"targetId": self._target_id, "flatten": True})
        self._session_id = res["sessionId"]
        
        # Enable page
        await self._send_session("Page.enable")
        self._ws = self._browser_ws # Backwards compatibility for _evaluate which now uses _send_session
        self._msg_id = 0
        self._csrf_installed = False
        logger.info("CDP WebSocket connected to dedicated hidden target")

    async def ensure_ready(self):
        """Connect and prepare the transport for catalog capture by navigating to Uber Eats."""
        if self._ws is None :
            await self.connect()
            
        await self._send_session("Page.navigate", {"url": "https://www.ubereats.com/"})
        await asyncio.sleep(4) # Wait for page and cookies
        
        await self._install_csrf_interceptor()
        return await self._check_login_state()

    async def close(self):
        """Close the target and disconnect."""
        if hasattr(self, '_target_id') and self._target_id:
            await self._send_global("Target.closeTarget", {"targetId": self._target_id})
            
        if hasattr(self, '_browser_ws') and self._browser_ws :
            await self._browser_ws.close()
            
        self._ws = None
        self._browser_ws = None
        self._csrf_installed = False

    # ------------------------------------------------------------------
    # CDP messaging
    # ------------------------------------------------------------------

    async def _send_global(self, method, params=None):
        msg_id = self._next_id()
        payload = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        await self._browser_ws.send(json.dumps(payload))
        while True:
            raw = await asyncio.wait_for(self._browser_ws.recv(), timeout=FETCH_TIMEOUT)
            data = json.loads(raw)
            if data.get("id") == msg_id:
                if "error" in data:
                    raise RuntimeError(f"Global CDP error: {data['error']}")
                return data.get("result", {})

    async def _send_session(self, method, params=None):
        msg_id = self._next_id()
        payload = {"id": msg_id, "method": method, "sessionId": self._session_id}
        if params:
            payload["params"] = params
        await self._browser_ws.send(json.dumps(payload))
        while True:
            raw = await asyncio.wait_for(self._browser_ws.recv(), timeout=FETCH_TIMEOUT)
            data = json.loads(raw)
            if data.get("id") == msg_id:
                if "error" in data:
                    raise RuntimeError(f"Session CDP error: {data['error']}")
                return data.get("result", {})
                
    async def _send(self, method, params=None):
        return await self._send_session(method, params)

    async def _evaluate(self, expression, await_promise=False):
        """Evaluate JavaScript in the page context and return the result value."""
        params = {"expression": expression}
        if await_promise:
            params["awaitPromise"] = True
        result = await self._send_session("Runtime.evaluate", params)
        inner = result.get("result", {})
        if inner.get("type") == "undefined":
            return None
        if "exceptionDetails" in result:
            raise RuntimeError(
                f"JS exception: {result['exceptionDetails'].get('text', 'unknown')}"
            )
        return inner.get("value")

    # ------------------------------------------------------------------
    # CSRF & login detection
    # ------------------------------------------------------------------

    async def _install_csrf_interceptor(self):
        """Install a minimal XHR interceptor to capture the CSRF token in-browser.
        The token value never leaves the browser context."""
        if self._csrf_installed:
            return
        js = """
        (() => {
            if (window.__dh_csrf) return 'already_installed';
            const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
            XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
                if (name.toLowerCase() === 'x-csrf-token') {
                    window.__dh_csrf = value;
                }
                return origSetHeader.call(this, name, value);
            };
            return 'installed';
        })()
        """
        result = await self._evaluate(js)
        self._csrf_installed = True
        logger.debug("CSRF interceptor: %s", result)

    async def _has_csrf(self):
        """Check whether the CSRF token has been captured in-browser."""
        result = await self._evaluate(
            "window.__dh_csrf ? window.__dh_csrf.length : 0"
        )
        return bool(result and result > 0)

    async def _trigger_csrf_capture(self):
        """Scroll the page to trigger an XHR that will set the CSRF token."""
        await self._evaluate(
            "window.scrollTo(0, document.body.scrollHeight); void(0);"
        )
        await asyncio.sleep(2)
        return await self._has_csrf()

    async def _check_login_state(self):
        """Detect whether the user is logged in to Uber Eats."""
        current_url = await self._evaluate("window.location.href") or ""

        if "auth.uber.com" in current_url:
            return LOGIN_REQUIRED
        if "challenge" in current_url.lower():
            return CHALLENGE_REQUIRED

        # Check page content for login indicators
        has_login_btn = await self._evaluate(
            "document.body.innerText.includes('Iniciar sesión') "
            "&& !document.body.innerText.includes('Cerrar sesión') "
            "&& document.querySelectorAll('a[href*=\"/store/\"]').length === 0"
        )
        if has_login_btn:
            return LOGIN_REQUIRED

        return READY

    # ------------------------------------------------------------------
    # Store navigation & capture
    # ------------------------------------------------------------------

    async def navigate_to_store(self, store_url):
        """Navigate the browser tab to a store URL."""
        await self._send("Page.enable")
        await self._send("Page.navigate", {"url": store_url})
        await asyncio.sleep(4)  # Wait for initial page load


    async def capture_store(self, store_uuid, max_pages=15):
        """Capture a complete store catalog using browser-context fetch."""
        
        if not self._ws:
            try:
                await self.connect()
            except Exception as e:
                return {"status": "empty", "error": str(e)}

        merged_data = {
            "uuid": store_uuid,
            "sections": [],
            "catalogSectionsMap": {}
        }
        
        pages_fetched = 0
        offset = 0
        total_raw_items = 0

        for page in range(max_pages):
            try:
                page_result = await self._fetch_store_page(store_uuid, offset)
            except Exception as e:
                logger.warning("Store page error at offset %d: %s", offset, e)
                break
            
            if page_result is None or page_result.get("error"):
                logger.warning("Page result None or error: %s", page_result)
                break

            pages_fetched += 1
            
            # Merge top-level fields on the first page
            if page == 0:
                merged_data["title"] = page_result.get("storeTitle")
                merged_data["slug"] = page_result.get("slug")
                merged_data["isOpen"] = page_result.get("isOpen")
                merged_data["isOrderable"] = page_result.get("isOrderable")
            
            # Accumulate sections
            sections = page_result.get("sections", [])
            merged_data["sections"].extend(sections)
            
            # Accumulate catalogSectionsMap
            csm = page_result.get("catalogSectionsMap", {})
            items_in_page = 0
            for k, v in csm.items():
                if k not in merged_data["catalogSectionsMap"]:
                    merged_data["catalogSectionsMap"][k] = []
                merged_data["catalogSectionsMap"][k].extend(v)
                
                # Estimate items for completeness metrics
                for el in v:
                    if el.get("type") in ("VERTICAL_GRID", "HORIZONTAL_GRID"):
                        items_in_page += len(el.get("payload", {}).get("standardItemsPayload", {}).get("catalogItems", []))
            
            total_raw_items += items_in_page
            
            paging = page_result.get("pagingInfo") or {}
            new_offset = paging.get("offset")
            
            # If no items were found, or the offset didn't advance, stop.
            if not new_offset or new_offset <= offset or items_in_page == 0:
                break
            offset = new_offset
            await asyncio.sleep(INTER_PAGE_DELAY)

        completeness = "COMPLETE" if pages_fetched > 0 and total_raw_items > 0 else "FAILED"
        if pages_fetched > 0 and offset > 0 and pages_fetched >= max_pages:
            completeness = "PARTIAL"

        return {
            "status": "success" if total_raw_items > 0 else "empty",
            "store_uuid": store_uuid,
            "completeness": completeness,
            "pages_fetched": pages_fetched,
            "products_raw": total_raw_items,
            "raw_payload": merged_data,
        }
    async def _fetch_store_page(self, store_uuid, offset):
        """Fetch one page of getStoreV1 via browser-context fetch."""
        fetch_js = f'''
        (async () => {{
            try {{
                const resp = await fetch('/_p/api/getStoreV1?localeCode=mx', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'x-csrf-token': 'x'
                    }},
                    body: JSON.stringify({{
                        storeUuid: '{store_uuid}',
                        catalogSectionOffset: {offset}
                    }})
                }});
                if (resp.status === 403) return JSON.stringify({{error: 'csrf_rejected', httpStatus: 403}});
                if (resp.status === 401) return JSON.stringify({{error: 'login_required', httpStatus: 401}});
                if (!resp.ok) return JSON.stringify({{error: 'http_' + resp.status, httpStatus: resp.status}});

                const data = await resp.json();
                if (data.status !== 'success') return JSON.stringify({{error: 'api_' + (data.status || 'unknown')}});

                const d = data.data || {{}};
                const sections = d.sections || [];
                const csm = d.catalogSectionsMap || {{}};

                // Simply return the raw structures needed by parser.py
                return JSON.stringify({{
                    status: data.status,
                    storeTitle: d.title,
                    storeUuid: d.uuid,
                    slug: d.slug,
                    isOpen: d.isOpen,
                    isOrderable: d.isOrderable,
                    sections: sections,
                    catalogSectionsMap: csm,
                    pagingInfo: d.catalogSectionPagingInfo
                }});
            }} catch (e) {{
                return JSON.stringify({{error: e.message}});
            }}
        }})()
        '''
        try:
            result_str = await self._evaluate(fetch_js, await_promise=True)
            if not result_str:
                return {"error": "empty_response"}
            return json.loads(result_str)
        except TimeoutError:
            return {"error": CAPTURE_TIMEOUT}
        except Exception as e:
            return {"error": str(e)}
    # ------------------------------------------------------------------
    # Multi-store sync
    # ------------------------------------------------------------------



    async def fetch_feed_v1(self, lat, lng):
        js = '''
        (async () => {
            const resp = await fetch('/_p/api/getFeedV1?localeCode=mx', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-csrf-token': 'x'
                },
                body: JSON.stringify({
                    userQuery: "supermercado"
                })
            });
            return await resp.json();
        })();
        '''
        res = await self._send_session("Runtime.evaluate", {"expression": js, "awaitPromise": True, "returnByValue": True})
        val = res.get("result", {}).get("value")
        if not val or "error" in val:
            raise RuntimeError(f"Failed to fetch feed: {val}")
        return val

    async def fetch_store_v1(self, store_uuid, offset=0):
        js = f'''
        (async () => {{
            const resp = await fetch('/_p/api/getStoreV1?localeCode=mx', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'x-csrf-token': 'x'
                }},
                body: JSON.stringify({{
                    storeUuid: '{store_uuid}',
                    catalogSectionOffset: {offset}
                }})
            }});
            return await resp.json();
        }})();
        '''
        res = await self._send_session("Runtime.evaluate", {"expression": js, "awaitPromise": True, "returnByValue": True})
        val = res.get("result", {}).get("value")
        if not val or "error" in val:
            raise RuntimeError(f"Failed to fetch store: {val}")
        return val

    async def capture_stores(self, store_urls_or_uuids, on_progress=None):
        """Capture multiple stores sequentially.

        Args:
            store_urls_or_uuids: List of (url, uuid, label) tuples.
            on_progress: Optional callback(label, status, result).

        Returns:
            List of capture results with status per store.
        """
        results = []
        for i, (url, uuid, label) in enumerate(store_urls_or_uuids):
            logger.info("Capturing store %d/%d: %s", i + 1, len(store_urls_or_uuids), label)
            try:
                # Navigate to store page first (establishes context)
                await self.navigate_to_store(url)

                result = await self.capture_store(uuid)
                result["label"] = label
                result["url"] = url

                if on_progress:
                    on_progress(label, result.get("completeness", "UNKNOWN"), result)

            except Exception as e:
                result = {
                    "status": "error",
                    "error": str(e),
                    "label": label,
                    "url": url,
                    "store_uuid": uuid,
                    "completeness": "FAILED",
                }
                if on_progress:
                    on_progress(label, "FAILED", result)

            results.append(result)

            if i < len(store_urls_or_uuids) - 1:
                await asyncio.sleep(INTER_STORE_DELAY)

        return results
