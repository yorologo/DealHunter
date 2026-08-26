import asyncio
import json
import urllib.request
import websockets

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    for tab in tabs:
        if "ubereats.com" in tab.get("url", "") and "webSocketDebuggerUrl" in tab:
            page_ws = tab["webSocketDebuggerUrl"]
            break

    async with websockets.connect(page_ws, ping_interval=None, max_size=50_000_000) as ws:
        js_code = """
        (async () => {
            const res = await fetch("https://www.ubereats.com/_p/api/getFeedV1?localeCode=mx", {
                method: "POST",
                headers: {
                    "content-type": "application/json",
                    "x-csrf-token": "x"
                },
                body: JSON.stringify({
                    "userQuery": "pizza"
                })
            });
            return await res.text();
        })();
        """
        await ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "awaitPromise": True,
                "returnByValue": True
            }
        }))
        
        resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(resp)
        val = data.get("result", {}).get("result", {}).get("value")
        print(val[:1000] if val else "NONE")
        with open("scratch/search_res.json", "w") as f:
            f.write(val if val else "")

asyncio.run(main())
