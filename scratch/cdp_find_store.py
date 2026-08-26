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
            
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": "https://www.ubereats.com/"}}))
        await asyncio.sleep(4)
        
        # Get Redux state
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
                    if state_str == "{}":
                        # Try to get links instead
                        req2 = next_id()
                        await ws.send(json.dumps({
                            "id": req2,
                            "method": "Runtime.evaluate",
                            "params": {"expression": "Array.from(document.querySelectorAll('a[href*=\"/store/\"]')).map(a => a.href).join(',')"}
                        }))
                        resp2 = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        data2 = json.loads(resp2)
                        print("Store links:", data2["result"]["result"]["value"])
                    else:
                        print("Got state length:", len(state_str))
                    break
            except asyncio.TimeoutError:
                break

asyncio.run(main())
