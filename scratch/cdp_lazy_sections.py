"""
Stage E+F: Trigger lazy section loading via browser-context fetch.
The getStoreV1 response shows catalogSectionPagingInfo.offset=15, isFirstPage=false.
This means sections are loaded by calling getStoreV1 with different catalogSectionOffset values.
The initial SSR had offset 0 (7 sections), the scroll-triggered call had offset 7 (6 more sections).
We need to call with incrementing offsets until all sections are fetched.

Strategy: Use Runtime.evaluate to call fetch() from within the browser context,
letting the browser handle cookies/CSRF automatically.
"""
import asyncio
import json
import hashlib
import time
import os
import urllib.request
import websockets

RESEARCH_DIR = os.path.expanduser("~/.local/share/DealHunter/research/uber-eats/cdp")
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222

async def main():
    req = urllib.request.urlopen(f"http://{CDP_HOST}:{CDP_PORT}/json", timeout=2)
    tabs = json.loads(req.read())
    page_ws = None
    for tab in tabs:
        if tab.get("type") == "page" and "ubereats" in tab.get("url", ""):
            page_ws = tab.get("webSocketDebuggerUrl")
            break
    if not page_ws:
        page_ws = tabs[0]["webSocketDebuggerUrl"]

    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        msg_id = 1
        def next_id():
            nonlocal msg_id
            msg_id += 1
            return msg_id - 1

        # First, get current page URL to extract store UUID
        req_id = next_id()
        await ws.send(json.dumps({
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {"expression": "window.location.href"}
        }))
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(resp)
            if data.get("id") == req_id:
                current_url = data["result"]["result"]["value"]
                print("Current URL:", current_url)
                break

        # Use browser-context fetch to call getStoreV1 with offset 0
        # The browser will include its own cookies/CSRF automatically
        store_uuid = "50c604ad-6fe5-5953-9dfc-517039837504"  # Soriana
        
        all_sections = []
        all_items = {}
        offset = 0
        
        for page in range(10):  # safety limit
            print(f"\n--- Fetching offset={offset} ---")
            
            # Build the fetch call to execute in browser context
            fetch_js = f"""
            (async () => {{
                try {{
                    const resp = await fetch('/_p/api/getStoreV1?localeCode=mx', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            storeUuid: '{store_uuid}',
                            catalogSectionOffset: {offset}
                        }})
                    }});
                    const data = await resp.json();
                    return JSON.stringify({{
                        status: data.status,
                        sections: (data.data?.sections || []).length,
                        sectionTitles: (data.data?.sections || []).map(s => s.title),
                        catalogKeys: Object.keys(data.data?.catalogSectionsMap || {{}}).length,
                        pagingInfo: data.data?.catalogSectionPagingInfo,
                        itemCount: Object.values(data.data?.catalogSectionsMap || {{}}).flat()
                            .filter(e => e.type === 'HORIZONTAL_GRID' || e.type === 'VERTICAL_GRID')
                            .reduce((sum, e) => sum + (e.payload?.standardItemsPayload?.catalogItems?.length || 0), 0),
                        bodyLength: JSON.stringify(data).length
                    }});
                }} catch (e) {{
                    return JSON.stringify({{error: e.message}});
                }}
            }})()
            """
            
            req_id = next_id()
            await ws.send(json.dumps({
                "id": req_id,
                "method": "Runtime.evaluate",
                "params": {"expression": fetch_js, "awaitPromise": True}
            }))
            
            while True:
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(resp)
                    if data.get("id") == req_id:
                        result_str = data["result"]["result"]["value"]
                        result = json.loads(result_str)
                        
                        if "error" in result:
                            print(f"  ERROR: {result['error']}")
                            break
                        
                        print(f"  status: {result['status']}")
                        print(f"  sections: {result['sections']}")
                        print(f"  sectionTitles: {result['sectionTitles']}")
                        print(f"  catalogKeys: {result['catalogKeys']}")
                        print(f"  itemCount: {result['itemCount']}")
                        print(f"  pagingInfo: {result['pagingInfo']}")
                        print(f"  bodyLength: {result['bodyLength']}")
                        
                        paging = result.get("pagingInfo", {})
                        new_offset = paging.get("offset")
                        is_first = paging.get("isFirstPage", False)
                        
                        if result['sections'] == 0 or result['itemCount'] == 0:
                            print("\n  No more sections. DONE.")
                            break
                        
                        if new_offset and new_offset != offset:
                            offset = new_offset
                        else:
                            print("\n  No new offset. DONE.")
                            break
                        break
                except asyncio.TimeoutError:
                    print("  TIMEOUT waiting for response")
                    break
            else:
                continue
            
            if result.get('sections', 0) == 0 or result.get('itemCount', 0) == 0:
                break

asyncio.run(main())
