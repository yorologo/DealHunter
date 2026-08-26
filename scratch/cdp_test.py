import asyncio
import json
import urllib.request
import websockets

async def main():
    # 1. Get websocket URL of the first tab
    req = urllib.request.urlopen("http://127.0.0.1:9222/json")
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    
    async with websockets.connect(page_ws) as ws:
        msg_id = 1
        
        # Enable Network
        await ws.send(json.dumps({"id": msg_id, "method": "Network.enable"}))
        msg_id += 1
        
        # Enable Page
        await ws.send(json.dumps({"id": msg_id, "method": "Page.enable"}))
        msg_id += 1
        
        # Navigate
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Page.navigate",
            "params": {"url": "https://www.ubereats.com/"}
        }))
        
        # Wait a bit
        await asyncio.sleep(5)
        
        # Get page content to check login
        msg_id += 1
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.body.innerText.substring(0, 500)"}
        }))
        
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                if data.get("id") == msg_id:
                    print("Page content snippet:", data["result"]["result"]["value"])
                    break
            except asyncio.TimeoutError:
                break
                
asyncio.run(main())
