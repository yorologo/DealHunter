import asyncio
import json
import urllib.request
import websockets

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    
    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        msg_id = 1
        def next_id(): nonlocal msg_id; msg_id += 1; return msg_id - 1
            
        url = "https://www.ubereats.com/mx/store/soriana-belenes/UMYErW_lWVOd_FFwOYN1BA"
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": url}}))
        
        await asyncio.sleep(8)
        
        # Try to get REDUX or REACT_QUERY state
        req_id = next_id()
        await ws.send(json.dumps({
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {"expression": "JSON.stringify(window.__REDUX_STATE__ || window.__REACT_QUERY_STATE__ || {})"}
        }))
        
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                if data.get("id") == req_id:
                    state_str = data["result"]["result"]["value"]
                    print("State length:", len(state_str))
                    with open("scratch/soriana_state.json", "w") as f:
                        f.write(state_str)
                    break
            except asyncio.TimeoutError:
                break

asyncio.run(main())
