import asyncio
import json
import urllib.request
import websockets
import time
import os
import hashlib

async def main():
    req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2)
    tabs = json.loads(req.read())
    
    page_ws = None
    for tab in tabs:
        if "ubereats.com" in tab.get("url", "") and "webSocketDebuggerUrl" in tab:
            page_ws = tab["webSocketDebuggerUrl"]
            break
            
    if not page_ws:
        print("No Uber Eats tab found. Using first available tab for testing.")
        page_ws = tabs[0]["webSocketDebuggerUrl"]

    print(f"Connecting to: {page_ws}")
    
    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        msg_id = 1
        def next_id(): nonlocal msg_id; msg_id += 1; return msg_id - 1
            
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))
        await ws.send(json.dumps({"id": next_id(), "method": "Page.enable"}))
        
        # We will listen for responses. 
        # But we need to refresh the page to trigger getStoreV1, or navigate.
        url = "https://www.ubereats.com/mx/store/soriana-belenes/UMYErW_lWVOd_FFwOYN1BA"
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": url}}))
        
        start_time = time.time()
        
        while time.time() - start_time < 20:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                
                if data.get("method") == "Network.responseReceived":
                    res_params = data["params"]
                    response = res_params.get("response", {})
                    res_url = response.get("url", "")
                    
                    if "getStoreV1" in res_url:
                        req_id = res_params["requestId"]
                        print(f"\n[+] Found getStoreV1 RESPONSE: {res_url}")
                        
                        # Request the body
                        req_body_id = next_id()
                        await ws.send(json.dumps({
                            "id": req_body_id,
                            "method": "Network.getResponseBody",
                            "params": {"requestId": req_id}
                        }))
                        
                        # Wait for the body response
                        while time.time() - start_time < 25:
                            body_resp_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                            body_data = json.loads(body_resp_raw)
                            
                            if body_data.get("id") == req_body_id:
                                result = body_data.get("result", {})
                                body = result.get("body", "")
                                
                                # Summary info
                                print("URL:", res_url)
                                print("STATUS:", response.get("status"))
                                print("MIME:", response.get("mimeType"))
                                print("OPERATION: getStoreV1")
                                
                                body_bytes = len(body.encode('utf-8'))
                                print("BODY_BYTES:", body_bytes)
                                
                                try:
                                    json_body = json.loads(body)
                                    print("JSON: YES")
                                    
                                    data_node = json_body.get("data", {})
                                    print("TOP_KEYS:", list(json_body.keys()))
                                    
                                    store_node = data_node.get("store", {})
                                    print("STORE_ID:", store_node.get("storeUuid"))
                                    
                                    catalog = store_node.get("catalog", {})
                                    sections = catalog.get("sections", [])
                                    print("SECTIONS:", len(sections))
                                    
                                    items = 0
                                    for sec in sections:
                                        items += len(sec.get("catalogItems", []))
                                    print("ITEMS:", items)
                                    
                                    # Lazy hints
                                    print("LAZY_HINTS: None yet")
                                    
                                    # Save to file
                                    out_dir = os.path.expanduser("~/.local/share/DealHunter/research/uber-eats/cdp/")
                                    os.makedirs(out_dir, exist_ok=True)
                                    out_file = os.path.join(out_dir, "getstore_v1_resp.json")
                                    with open(out_file, "w") as f:
                                        json.dump(json_body, f, indent=2)
                                    
                                    print("\nSaved to:", out_file)
                                    print("SHA256:", hashlib.sha256(body.encode('utf-8')).hexdigest())
                                    
                                except Exception as e:
                                    print("JSON: NO or ERROR parsing:", e)
                                
                                return
                        
            except asyncio.TimeoutError:
                continue

asyncio.run(main())
