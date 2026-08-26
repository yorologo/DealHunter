import asyncio
import json
import urllib.request
import websockets
import time

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    for tab in tabs:
        if "ubereats.com" in tab.get("url", "") and "webSocketDebuggerUrl" in tab:
            page_ws = tab["webSocketDebuggerUrl"]
            break

    async with websockets.connect(page_ws, ping_interval=None, max_size=50_000_000) as ws:
        msg_id = 999
        store_id = "50c604ad-6fe5-5953-9dfc-517039837504"
        js_code = f"""
        (async () => {{
            try {{
                const res = await fetch("https://www.ubereats.com/_p/api/getStoreV1?localeCode=mx", {{
                    method: "POST",
                    headers: {{
                        "content-type": "application/json",
                        "x-csrf-token": "x"
                    }},
                    body: JSON.stringify({{
                        "storeUuid": "{store_id}",
                        "catalogSectionOffset": 0
                    }})
                }});
                const data = await res.json();
                const str = JSON.stringify(data.data.catalogSectionsMap["{store_id}"]);
                return str;
            }} catch (e) {{
                return `EXCEPTION:${{e.message}}`;
            }}
        }})();
        """
        
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "awaitPromise": True,
                "returnByValue": True
            }
        }))
        
        start = time.time()
        while time.time() - start < 10:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                print("GOT MSG ID:", data.get("id"), "METHOD:", data.get("method"))
                if data.get("id") == msg_id:
                    print("GOT TARGET MESSAGE!")
                    val = data.get("result", {}).get("result", {}).get("value")
                    if val:
                        print("VALUE LENGTH:", len(val))
                    else:
                        print("NO VALUE, full payload:", str(data)[:500])
                    return
            except asyncio.TimeoutError:
                print("TIMEOUT TICK")
                continue

asyncio.run(main())
