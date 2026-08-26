import asyncio
import json
import urllib.request
import websockets
import time

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]

    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        msg_id = 1
        def next_id(): nonlocal msg_id; msg_id += 1; return msg_id - 1
            
        js_code = """
        (async () => {
            try {
                const res = await fetch("https://www.ubereats.com/_p/api/getStoreV1?localeCode=mx", {
                    method: "POST",
                    headers: {
                        "content-type": "application/json",
                        "x-csrf-token": "x"
                    },
                    body: JSON.stringify({
                        "storeUuid": "50c604ad-6fe5-5953-9dfc-517039837504",
                        "catalogSectionOffset": 0
                    })
                });
                if (!res.ok) {
                    return `HTTP Error: ${res.status}`;
                }
                const data = await res.json();
                return JSON.stringify(data.data.catalogSectionsMap["50c604ad-6fe5-5953-9dfc-517039837504"].length);
            } catch (e) {
                return `Exception: ${e.message}`;
            }
        })();
        """
        
        await ws.send(json.dumps({
            "id": next_id(),
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "awaitPromise": True,
                "returnByValue": True
            }
        }))
        
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                if "result" in data:
                    print("FETCH RESULT:", data["result"])
                    return
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
