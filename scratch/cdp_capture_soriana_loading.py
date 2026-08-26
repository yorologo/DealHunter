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
            print("Scrolling...")
            await ws.send(json.dumps({
                "id": next_id(),
                "method": "Runtime.evaluate",
                "params": {"expression": "window.scrollTo(0, document.body.scrollHeight); setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 1000);"}
            }))
        
        asyncio.create_task(trigger_scroll())
        
        pending_requests = {}
        
        while time.time() - start_time < 20:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                
                if data.get("method") == "Network.responseReceived":
                    res_url = data["params"]["response"]["url"]
                    if "getStoreV1" in res_url:
                        req_id = data["params"]["requestId"]
                        print(f"Found getStoreV1 headers: {res_url}")
                        pending_requests[req_id] = True
                        
                elif data.get("method") == "Network.loadingFinished":
                    req_id = data["params"]["requestId"]
                    if req_id in pending_requests:
                        print(f"Loading finished for {req_id}, getting body...")
                        await ws.send(json.dumps({
                            "id": next_id(), 
                            "method": "Network.getResponseBody", 
                            "params": {"requestId": req_id}
                        }))
                        
                elif data.get("id"):
                    if "error" in data:
                        print("Got error for ID", data["id"], ":", data["error"])
                    elif "result" in data and "body" in data["result"]:
                        body = data["result"]["body"]
                        print("Body length:", len(body))
                        with open("scratch/soriana_getstore.json", "w") as f:
                            f.write(body)
                        break
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
