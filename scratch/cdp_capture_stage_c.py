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
    
    page_ws = tabs[0]["webSocketDebuggerUrl"]
    for tab in tabs:
        if "ubereats.com" in tab.get("url", "") and "webSocketDebuggerUrl" in tab:
            page_ws = tab["webSocketDebuggerUrl"]
            break

    print(f"Connecting to: {page_ws}")
    
    async with websockets.connect(page_ws, ping_interval=None, max_size=20_000_000) as ws:
        msg_id = 1
        def next_id(): nonlocal msg_id; msg_id += 1; return msg_id - 1
            
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))
        await ws.send(json.dumps({"id": next_id(), "method": "Page.enable"}))
        
        url = "https://www.ubereats.com/mx/store/soriana-belenes/UMYErW_lWVOd_FFwOYN1BA"
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": url}}))
        
        start_time = time.time()
        
        async def trigger_scroll():
            await asyncio.sleep(4)
            await ws.send(json.dumps({
                "id": next_id(),
                "method": "Runtime.evaluate",
                "params": {"expression": "window.scrollTo(0, document.body.scrollHeight); setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 1000);"}
            }))
        
        asyncio.create_task(trigger_scroll())
        
        req_metadata = {}
        
        while time.time() - start_time < 20:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(resp)
                
                if data.get("method") == "Network.requestWillBeSent":
                    req_data = data["params"]["request"]
                    req_id = data["params"]["requestId"]
                    res_url = req_data["url"]
                    if "getStoreV1" in res_url:
                        post_data = req_data.get("postData", "")
                        req_metadata[req_id] = {
                            "method": req_data["method"],
                            "url": res_url,
                            "postData": post_data
                        }
                        print(f"\n[+] Found getStoreV1 REQUEST (ID: {req_id})")
                        print(f"URL: {res_url}")
                        print(f"PostData: {post_data}")
                
                elif data.get("method") == "Network.responseReceived":
                    res_params = data["params"]
                    response = res_params.get("response", {})
                    res_url = response.get("url", "")
                    req_id = res_params["requestId"]
                    
                    if "getStoreV1" in res_url and req_id in req_metadata:
                        print(f"\n[+] Found getStoreV1 RESPONSE (ID: {req_id})")
                        
                        req_body_id = next_id()
                        await ws.send(json.dumps({
                            "id": req_body_id,
                            "method": "Network.getResponseBody",
                            "params": {"requestId": req_id}
                        }))
                        
                        while time.time() - start_time < 25:
                            body_resp_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                            body_data = json.loads(body_resp_raw)
                            
                            if body_data.get("id") == req_body_id:
                                result = body_data.get("result", {})
                                body = result.get("body", "")
                                
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
                                    
                                    catalog = data_node.get("catalog", {})
                                    sections = catalog.get("sections", [])
                                    print("SECTIONS:", len(sections))
                                    
                                    items = 0
                                    for sec in sections:
                                        items += len(sec.get("catalogItems", []))
                                    print("ITEMS:", items)
                                    
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
