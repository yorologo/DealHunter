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
            
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))
        await ws.send(json.dumps({"id": next_id(), "method": "Page.enable"}))
        
        async def trigger_scroll():
            await asyncio.sleep(2)
            await ws.send(json.dumps({
                "id": next_id(),
                "method": "Runtime.evaluate",
                "params": {"expression": "window.scrollTo(0, document.body.scrollHeight);"}
            }))
        
        asyncio.create_task(trigger_scroll())
        
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                method = data.get("method")
                
                if method == "Network.requestWillBeSent":
                    req_data = data["params"]["request"]
                    res_url = req_data["url"]
                    if "getStoreV1" in res_url:
                        headers = req_data.get("headers", {})
                        print("Headers:", {k: v for k, v in headers.items() if k.lower() not in ["cookie", "authorization"]})
                        return
                        
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
