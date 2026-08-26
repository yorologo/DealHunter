import asyncio
import json
import urllib.request
import websockets
import time

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]

    async with websockets.connect(page_ws, ping_interval=None, max_size=50_000_000) as ws:
        msg_id = 999
        store_id = "c217523a-98fb-5e53-afbe-732c723ed2a2"
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
                        "storeUuid": "{store_id}"
                    }})
                }});
                const data = await res.json();
                return JSON.stringify(data);
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
        while time.time() - start < 15:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(resp)
                if data.get("id") == msg_id:
                    val = data.get("result", {}).get("result", {}).get("value")
                    try:
                        parsed = json.loads(val)
                        print("KEYS:", parsed.keys())
                        print("DATA KEYS:", parsed.get("data", {}).keys())
                        csm = parsed.get("data", {}).get("catalogSectionsMap", {})
                        if csm:
                            print("CSM STORES:", csm.keys())
                            if store_id in csm:
                                print("CSM SECTIONS:", len(csm[store_id]))
                        else:
                            print("NO CSM")
                    except:
                        print("RAW:", val[:500])
                    return
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
