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
            
        req_id = next_id()
        await ws.send(json.dumps({
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.documentElement.outerHTML"}
        }))
        
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                if data.get("id") == req_id:
                    html = data["result"]["result"]["value"]
                    print("HTML length:", len(html))
                    with open("scratch/soriana.html", "w") as f:
                        f.write(html)
                    break
            except asyncio.TimeoutError:
                break

asyncio.run(main())
