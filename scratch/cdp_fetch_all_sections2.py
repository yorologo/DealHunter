import asyncio
import json
import urllib.request
import websockets
import time
import os

async def fetch_offset(ws, store_id, offset):
    msg_id = int(time.time() * 1000)
    
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
                    "catalogSectionOffset": {offset}
                }})
            }});
            if (!res.ok) {{
                return `HTTP_ERROR:${{res.status}}`;
            }}
            const data = await res.json();
            const csm = data.data.catalogSectionsMap;
            if (!csm || !csm["{store_id}"]) {{
                return "NO_SECTIONS";
            }}
            return JSON.stringify(csm["{store_id}"]);
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
                res_val = data.get("result", {}).get("result", {}).get("value")
                if res_val is None:
                    return None
                if str(res_val).startswith("HTTP_ERROR") or str(res_val).startswith("EXCEPTION") or str(res_val) == "NO_SECTIONS":
                    return res_val
                return json.loads(res_val)
        except asyncio.TimeoutError:
            continue
            
    return "TIMEOUT"

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = None
    
    for tab in tabs:
        if "ubereats.com" in tab.get("url", "") and "webSocketDebuggerUrl" in tab:
            page_ws = tab["webSocketDebuggerUrl"]
            break
            
    if not page_ws:
        print("No Uber Eats tab found! Using tab[0]")
        page_ws = tabs[0]["webSocketDebuggerUrl"]

    print(f"Connecting to: {page_ws}")
    
    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        store_id = "50c604ad-6fe5-5953-9dfc-517039837504" # Soriana Belenes
        offset = 0
        all_sections = []
        all_items = 0
        
        while True:
            print(f"Fetching offset {offset}...")
            sections = await fetch_offset(ws, store_id, offset)
            
            if isinstance(sections, str):
                print(f"Error or end: {sections}")
                break
                
            if not sections:
                print("Empty response, assuming end.")
                break
                
            print(f"Got {len(sections)} sections")
            
            items_in_batch = 0
            for sec in sections:
                items = sec.get("payload", {}).get("standardItemsPayload", {}).get("catalogItems", [])
                items_in_batch += len(items)
                
            print(f"Items in this batch: {items_in_batch}")
            all_sections.extend(sections)
            all_items += items_in_batch
            
            if len(sections) == 0:
                break
                
            offset += len(sections)
            
        print("\n=== SUMMARY ===")
        print(f"Total sections fetched: {len(all_sections)}")
        print(f"Total items found: {all_items}")
        
        out_dir = os.path.expanduser("~/.local/share/DealHunter/research/uber-eats/cdp/")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "soriana_all_sections.json"), "w") as f:
            json.dump(all_sections, f)

asyncio.run(main())
