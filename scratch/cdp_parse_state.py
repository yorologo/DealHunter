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
        # Let's ask the page to find the script and parse it exactly how Uber does, or just return the text.
        # Wait, if we just want the JSON, we can write a regex to replace \u0022 properly.
        # Actually, if we ask the page to do JSON.parse(document.getElementById('__REACT_QUERY_STATE__').textContent.replace(/\\u0022/g, '"')), let's see if it throws!
        expression = """
        (() => {
            const el = document.getElementById('__REACT_QUERY_STATE__');
            if (!el) return 'No element';
            let text = el.textContent;
            try {
                // Let's see how Uber decodes it. 
                // Maybe they decode URI components? 
                // Let's just return the keys of the parsed object if we can parse it.
                // Wait, Uber's code for unescaping is usually: text.replace(/\\\\u0022/g, '"') or something.
                // Let's just find where it's parsed.
                return 'Text length: ' + text.length;
            } catch (e) {
                return 'Error: ' + e.message;
            }
        })()
        """
        await ws.send(json.dumps({
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {"expression": expression}
        }))
        
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                if data.get("id") == req_id:
                    print("Result:", data["result"]["result"]["value"])
                    break
            except asyncio.TimeoutError:
                break

asyncio.run(main())
