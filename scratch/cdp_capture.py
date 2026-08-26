import asyncio
import json
import urllib.request
import websockets
import sys

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    
    async with websockets.connect(page_ws, ping_interval=None) as ws:
        msg_id = 1
        def next_id():
            nonlocal msg_id
            msg_id += 1
            return msg_id - 1
            
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))
        await ws.send(json.dumps({"id": next_id(), "method": "Page.enable"}))
        
        # Navigate to a store
        url = "https://www.ubereats.com/mx/store/7-eleven-isste-zapopan/cuusNxBjUY22Z6S_nS--AA" # uuid converted to base64url or just use direct URL if valid
        # Actually the UUID was 72ebad37-1063-518d-b667-a4bf9d2fbe00, let's just search for a known store or use Uber Eats home and click something.
        # Let's try to search or navigate to a category
        url = "https://www.ubereats.com/mx/store/7-eleven-isste-zapopan/cuusNxBjUY22Z6S_nS--AA"
        
        print(f"Navigating to {url}")
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": url}}))
        
        # Listen for Network.responseReceived
        responses_seen = set()
        
        timeout = 10
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                if data.get("method") == "Network.responseReceived":
                    req_id = data["params"]["requestId"]
                    res_url = data["params"]["response"]["url"]
                    if "getStoreV1" in res_url:
                        print(f"Found getStoreV1 response: {res_url}")
                        # get response body
                        req_body_id = next_id()
                        await ws.send(json.dumps({
                            "id": req_body_id, 
                            "method": "Network.getResponseBody", 
                            "params": {"requestId": req_id}
                        }))
                        
                elif data.get("id") and data.get("result", {}).get("body"):
                    print("Got response body for getStoreV1, length:", len(data["result"]["body"]))
                    break
                    
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
