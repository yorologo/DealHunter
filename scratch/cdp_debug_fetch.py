import asyncio
import json
import urllib.request
import websockets
import time

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = None
    for tab in tabs:
        if "ubereats.com" in tab.get("url", "") and "webSocketDebuggerUrl" in tab:
            page_ws = tab["webSocketDebuggerUrl"]
            break
            
    if not page_ws:
        page_ws = tabs[0]["webSocketDebuggerUrl"]

    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        
        js_code = """
        (async () => {
            console.log("STARTING FETCH");
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
                console.log("FETCH DONE", res.status);
                const text = await res.text();
                console.log("BODY LEN", text.length);
            } catch (e) {
                console.error("FETCH EXCEPTION", e.message);
            }
        })();
        """
        
        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code
            }
        }))
        
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                
                if data.get("method") == "Runtime.consoleAPICalled":
                    args = data["params"]["args"]
                    vals = [a.get("value") for a in args]
                    print("CONSOLE:", vals)
                    
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
