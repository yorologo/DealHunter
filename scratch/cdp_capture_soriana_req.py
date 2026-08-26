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
        
        url = "https://www.ubereats.com/mx/store/soriana-belenes/UMYErW_lWVOd_FFwOYN1BA"
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": url}}))
        
        start_time = time.time()
        
        async def trigger_scroll():
            await asyncio.sleep(4)
            await ws.send(json.dumps({
                "id": next_id(),
                "method": "Runtime.evaluate",
                "params": {"expression": "window.scrollTo(0, document.body.scrollHeight); setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 1000);"}
            }))
        
        asyncio.create_task(trigger_scroll())
        
        while time.time() - start_time < 20:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                
                if data.get("method") == "Network.requestWillBeSent":
                    req_data = data["params"]["request"]
                    res_url = req_data["url"]
                    if "getStoreV1" in res_url:
                        print(f"Found getStoreV1 REQUEST: {res_url}")
                        post_data = req_data.get("postData", "")
                        print("PostData:", post_data)
                        break
                        
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
