import asyncio
import json
import urllib.request
import websockets

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json")
    tabs = json.loads(req.read())
    
    # Let's find the Uber Eats tab or use the first one
    page_ws = None
    for tab in tabs:
        if "ubereats.com" in tab.get("url", ""):
            page_ws = tab["webSocketDebuggerUrl"]
            break
            
    if not page_ws:
        page_ws = tabs[0]["webSocketDebuggerUrl"]
        
    async with websockets.connect(page_ws) as ws:
        msg_id = 1
        
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {"expression": "Array.from(document.querySelectorAll('button, a')).map(el => el.innerText).filter(t => t.toLowerCase().includes('iniciar')).join(', ')"}
        }))
        
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                if data.get("id") == msg_id:
                    print("Login/Buttons found:", data["result"]["result"]["value"])
                    break
            except asyncio.TimeoutError:
                break
                
asyncio.run(main())
