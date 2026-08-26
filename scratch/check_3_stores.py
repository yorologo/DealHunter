import asyncio
import json
import urllib.request
import websockets
import time
import os
import uuid
import base64

def decode_uuid(b64u):
    b = base64.urlsafe_b64decode(b64u + '==')
    return str(uuid.UUID(bytes=b))

STORES = [
    ("KFC", "whdSOpj7XlOvvnMscj7Sog"),
    ("OXXO", "ldQv4KStXYCzcZ-zpCjhJA"),
    ("Soriana", "UMYErW_lWVOd_FFwOYN1BA")
]

msg_id_counter = 100

async def fetch_offset(ws, store_id, offset):
    global msg_id_counter
    msg_id_counter += 1
    msg_id = msg_id_counter
    
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

async def process_store(ws, name, store_uuid_b64):
    store_id = decode_uuid(store_uuid_b64)
    print(f"\n--- Processing {name} ({store_id}) ---")
    offset = 0
    all_sections = []
    all_items = 0
    
    while True:
        print(f"Fetching {name} offset {offset}...")
        sections = await fetch_offset(ws, store_id, offset)
        
        if isinstance(sections, str):
            print(f"[{name}] Error or end: {sections}")
            break
            
        if not sections:
            print(f"[{name}] Empty response, assuming end.")
            break
            
        items_in_batch = 0
        for sec in sections:
            items = sec.get("payload", {}).get("standardItemsPayload", {}).get("catalogItems", [])
            items_in_batch += len(items)
            
        print(f"[{name}] Got {len(sections)} sections, {items_in_batch} items")
        all_sections.extend(sections)
        all_items += items_in_batch
        
        if len(sections) == 0:
            break
            
        offset += len(sections)
        
    print(f"\n[{name}] SUMMARY: {len(all_sections)} sections, {all_items} items")

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    for tab in tabs:
        if "ubereats.com" in tab.get("url", "") and "webSocketDebuggerUrl" in tab:
            page_ws = tab["webSocketDebuggerUrl"]
            break

    print(f"Connecting to: {page_ws}")
    
    async with websockets.connect(page_ws, ping_interval=None, max_size=50_000_000) as ws:
        for name, b64 in STORES:
            await process_store(ws, name, b64)

asyncio.run(main())
