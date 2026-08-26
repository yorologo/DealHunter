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

    print(f"Connecting to: {page_ws}")
    
    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        msg_id = 1
        def next_id(): nonlocal msg_id; msg_id += 1; return msg_id - 1
            
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))
        await ws.send(json.dumps({"id": next_id(), "method": "Page.enable"}))
        
        url = "https://www.ubereats.com/mx/store/soriana-belenes/UMYErW_lWVOd_FFwOYN1BA"
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": url}}))
        
        start_time = time.time()
        
        while time.time() - start_time < 15:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                
                if data.get("method") == "Network.responseReceived":
                    res_url = data["params"]["response"]["url"]
                    if "api" in res_url or "graphql" in res_url or "getStoreV1" in res_url:
                        print(f"RESPONSE: {res_url}")
                elif data.get("method") == "Network.requestWillBeSent":
                    req_url = data["params"]["request"]["url"]
                    if "api" in req_url or "graphql" in req_url or "getStoreV1" in req_url:
                        print(f"REQUEST: {req_url}")
                        
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
