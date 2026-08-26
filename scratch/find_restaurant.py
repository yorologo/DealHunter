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
        await ws.send(json.dumps({"id": msg_id, "method": "Page.enable"}))
        msg_id += 1
        
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Page.navigate",
            "params": {"url": "https://www.ubereats.com/mx"}
        }))
        msg_id += 1
        
        await asyncio.sleep(5)
        
        js_code = """
        Array.from(document.querySelectorAll('a[href*="/store/"]')).map(a => a.href).slice(0, 5)
        """
        
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "returnByValue": True
            }
        }))
        
        start = time.time()
        while time.time() - start < 10:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                if data.get("id") == msg_id:
                    print("Found stores:", data.get("result", {}).get("result", {}).get("value"))
                    return
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
