"""
CSRF token isn't in visible cookies or meta tags.
It's likely in an httpOnly cookie or set via JS runtime.
Let's use CDP to check httpOnly cookies and also look at how existing XHR requests include it.
"""
import asyncio
import json
import urllib.request
import websockets

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
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

        # Use Network domain to intercept an existing XHR and see what headers Uber's JS sends
        # Let's check if we can find the csrf mechanism by looking at request headers
        # of recently sent requests
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))

        # Trigger a lightweight API call by scrolling
        req_id = next_id()
        await ws.send(json.dumps({
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {"expression": "window.scrollTo(0, 100); window.scrollTo(0, 0);"}
        }))
        
        import time
        start = time.time()
        found_headers = False
        while time.time() - start < 8:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                if data.get("method") == "Network.requestWillBeSent":
                    req_data = data["params"]["request"]
                    url = req_data.get("url", "")
                    if "_p/api/" in url:
                        headers = req_data.get("headers", {})
                        # Print header NAMES only, not values
                        header_names = list(headers.keys())
                        csrf_headers = [h for h in header_names if "csrf" in h.lower()]
                        print(f"URL: {url.split('ubereats.com')[-1][:60]}")
                        print(f"  Header names: {header_names}")
                        print(f"  CSRF headers: {csrf_headers}")
                        found_headers = True
                        break
            except asyncio.TimeoutError:
                continue
        
        if not found_headers:
            # Try to intercept by navigating to trigger getStoreV1
            print("No XHR observed from scroll. Checking cookies via CDP...")
            
            # Use Storage.getCookies to find httpOnly cookies
            req_id = next_id()
            await ws.send(json.dumps({
                "id": req_id,
                "method": "Network.getCookies",
                "params": {"urls": ["https://www.ubereats.com"]}
            }))
            
            while True:
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(resp)
                    if data.get("id") == req_id:
                        cookies = data["result"]["cookies"]
                        # Print only names and httpOnly status, NOT values
                        csrf_cookies = []
                        for c in cookies:
                            name = c.get("name", "")
                            if "csrf" in name.lower() or "token" in name.lower():
                                csrf_cookies.append({
                                    "name": name,
                                    "httpOnly": c.get("httpOnly"),
                                    "secure": c.get("secure"),
                                    "domain": c.get("domain"),
                                    "valueLength": len(c.get("value", ""))
                                })
                        print(f"Total cookies: {len(cookies)}")
                        print(f"CSRF/token cookies:")
                        for cc in csrf_cookies:
                            print(f"  {json.dumps(cc)}")
                        if not csrf_cookies:
                            # Check all httpOnly cookies 
                            http_only = [{"name": c["name"], "domain": c.get("domain")} for c in cookies if c.get("httpOnly")]
                            print(f"httpOnly cookies: {http_only}")
                        break
                except asyncio.TimeoutError:
                    break

asyncio.run(main())
