import asyncio
import json
import urllib.request
import websockets

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    
    async with websockets.connect(page_ws, ping_interval=None) as ws:
        msg_id = 1
        def next_id(): nonlocal msg_id; msg_id += 1; return msg_id - 1
            
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))
        
        # Navigate to home first, then to a store
        url = "https://www.ubereats.com/mx/store/7-eleven-isste-zapopan/cuusNxBjUY22Z6S_nS--AA"
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": url}}))
        
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 10:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                if data.get("method") == "Network.responseReceived":
                    res_url = data["params"]["response"]["url"]
                    if "getStoreV1" in res_url:
                        req_id = data["params"]["requestId"]
                        await ws.send(json.dumps({
                            "id": next_id(), 
                            "method": "Network.getResponseBody", 
                            "params": {"requestId": req_id}
                        }))
                elif "result" in data and "body" in data["result"]:
                    print("Body:", data["result"]["body"])
                    break
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
