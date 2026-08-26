"""
The browser-context fetch needs CSRF token from cookies.
Let's find how Uber's frontend gets it and use the same mechanism.
"""
import asyncio
import json
import urllib.request
import websockets

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222

async def main():
    req = urllib.request.urlopen(f"http://{CDP_HOST}:{CDP_PORT}/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = None
    for tab in tabs:
        if tab.get("type") == "page" and "ubereats" in tab.get("url", ""):
            page_ws = tab.get("webSocketDebuggerUrl")
            break
    if not page_ws:
        page_ws = tabs[0]["webSocketDebuggerUrl"]

    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        msg_id = 1
        def next_id():
            nonlocal msg_id
            msg_id += 1
            return msg_id - 1

        # Find how Uber gets csrf — it's typically from a cookie or meta tag
        # Let's check meta tags and document.cookie pattern (without printing values)
        check_js = """
        (() => {
            // Check for csrf in meta tags
            const metaCsrf = document.querySelector('meta[name="csrf-token"]');
            // Check if there's a function Uber uses
            const hasCookieUtil = typeof window.__BASEAPI_CSRF__ !== 'undefined';
            // Check cookie names (NOT values)
            const cookieNames = document.cookie.split(';').map(c => c.trim().split('=')[0]);
            const csrfCookies = cookieNames.filter(n => n.toLowerCase().includes('csrf'));
            return JSON.stringify({
                metaCsrfExists: !!metaCsrf,
                hasCookieUtil: hasCookieUtil,
                csrfCookieNames: csrfCookies,
                allCookieNames: cookieNames
            });
        })()
        """
        
        req_id = next_id()
        await ws.send(json.dumps({
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {"expression": check_js}
        }))
        
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(resp)
            if data.get("id") == req_id:
                print(json.dumps(json.loads(data["result"]["result"]["value"]), indent=2))
                break

        # Now try fetch with x-csrf-token header from cookie
        fetch_js = """
        (async () => {
            try {
                // Uber typically stores csrf in a cookie named 'csrftoken' or similar
                const cookies = document.cookie.split(';').reduce((acc, c) => {
                    const [k, v] = c.trim().split('=');
                    acc[k] = v;
                    return acc;
                }, {});
                
                // Try common csrf cookie names
                const csrfToken = cookies['_csrf'] || cookies['csrftoken'] || cookies['csrf'] || '';
                
                const resp = await fetch('/_p/api/getStoreV1?localeCode=mx', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-csrf-token': csrfToken
                    },
                    body: JSON.stringify({
                        storeUuid: '50c604ad-6fe5-5953-9dfc-517039837504',
                        catalogSectionOffset: 0
                    })
                });
                const text = await resp.text();
                return JSON.stringify({
                    httpStatus: resp.status,
                    bodyLength: text.length,
                    bodyPreview: text.substring(0, 200),
                    csrfFound: csrfToken.length > 0
                });
            } catch (e) {
                return JSON.stringify({error: e.message});
            }
        })()
        """
        
        req_id = next_id()
        await ws.send(json.dumps({
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {"expression": fetch_js, "awaitPromise": True}
        }))
        
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=10.0)
                data = json.loads(resp)
                if data.get("id") == req_id:
                    print("\nFetch result:")
                    print(json.dumps(json.loads(data["result"]["result"]["value"]), indent=2))
                    break
            except asyncio.TimeoutError:
                print("TIMEOUT")
                break

asyncio.run(main())
