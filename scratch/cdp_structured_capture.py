"""
Stage A+C: Structured CDP capture of getStoreV1 and lazy catalog operations.
Captures request metadata (sanitized) and response bodies.
Saves large payloads to disk, prints only summaries.
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
MAX_WS_SIZE = 20_000_000
TIMEOUT_NAVIGATION = 30
TIMEOUT_RECV = 1.0

# Sensitive headers to strip from captured request metadata
SENSITIVE_HEADERS = {"cookie", "authorization", "x-csrf-token", "set-cookie"}


def sanitize_request(req_data):
    """Extract safe request metadata, strip secrets."""
    return {
        "method": req_data.get("method"),
        "url": req_data.get("url"),
        "postData_keys": list(json.loads(req_data.get("postData", "{}")).keys()) if req_data.get("postData") else None,
        "postData_summary": {
            k: v for k, v in json.loads(req_data.get("postData", "{}")).items()
            if k not in ("cookies", "authorization")
        } if req_data.get("postData") else None,
    }


def summarize_getstore(body_json):
    """Summarize a getStoreV1 response body."""
    d = body_json.get("data", {})
    sections = d.get("sections", [])
    csm = d.get("catalogSectionsMap", {})
    total_items = 0
    categories = []
    for _k, elements in csm.items():
        for el in elements:
            if el.get("type") in ("VERTICAL_GRID", "HORIZONTAL_GRID"):
                sp = el.get("payload", {}).get("standardItemsPayload", {})
                title_obj = sp.get("title", {})
                cat_name = title_obj.get("text", "?") if isinstance(title_obj, dict) else str(title_obj)
                items = sp.get("catalogItems", [])
                total_items += len(items)
                categories.append({"name": cat_name, "items": len(items)})
    return {
        "status": body_json.get("status"),
        "store_uuid": d.get("uuid"),
        "store_title": d.get("title"),
        "is_open": d.get("isOpen"),
        "sections_declared": len(sections),
        "sections_fetched": len(csm),
        "total_items": total_items,
        "categories": categories,
        "completeness": "COMPLETE" if len(csm) >= len(sections) and len(sections) > 0 else "PARTIAL",
    }


async def capture_store(store_url, label="store"):
    """Navigate to a store and capture getStoreV1 + any lazy catalog responses."""
    req = urllib.request.urlopen(f"http://{CDP_HOST}:{CDP_PORT}/json", timeout=2)
    tabs = json.loads(req.read())

    # Find first page tab
    page_ws = None
    for tab in tabs:
        if tab.get("type") == "page" and "ubereats" in tab.get("url", ""):
            page_ws = tab.get("webSocketDebuggerUrl")
            break
    if not page_ws:
        for tab in tabs:
            if tab.get("type") == "page":
                page_ws = tab.get("webSocketDebuggerUrl")
                break
    if not page_ws:
        print("ERROR: No page tab found")
        return None

    async with websockets.connect(page_ws, ping_interval=None, max_size=MAX_WS_SIZE) as ws:
        msg_id = 1
        def next_id():
            nonlocal msg_id
            msg_id += 1
            return msg_id - 1

        # Enable CDP domains
        await ws.send(json.dumps({"id": next_id(), "method": "Network.enable"}))
        await ws.send(json.dumps({"id": next_id(), "method": "Page.enable"}))

        # Navigate
        print(f"Navigating to {store_url}")
        await ws.send(json.dumps({"id": next_id(), "method": "Page.navigate", "params": {"url": store_url}}))

        start_time = time.time()
        pending_requests = {}  # requestId -> sanitized request metadata
        captured_responses = []  # list of {request, response_summary, body_path}
        body_request_map = {}  # msg_id -> requestId

        # Schedule scroll to trigger lazy loading
        async def trigger_scroll():
            await asyncio.sleep(5)
            for i in range(3):
                await ws.send(json.dumps({
                    "id": next_id(),
                    "method": "Runtime.evaluate",
                    "params": {"expression": f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/3})"}
                }))
                await asyncio.sleep(1.5)

        asyncio.create_task(trigger_scroll())

        while time.time() - start_time < TIMEOUT_NAVIGATION:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT_RECV)
                data = json.loads(resp)

                # Track requests for Uber API calls
                if data.get("method") == "Network.requestWillBeSent":
                    req_data = data["params"]["request"]
                    url = req_data.get("url", "")
                    if "_p/api/" in url:
                        req_id = data["params"]["requestId"]
                        pending_requests[req_id] = {
                            "url": url,
                            "sanitized": sanitize_request(req_data),
                            "operation": url.split("/api/")[-1].split("?")[0] if "/api/" in url else "unknown",
                        }

                # Track response headers
                elif data.get("method") == "Network.responseReceived":
                    req_id = data["params"]["requestId"]
                    if req_id in pending_requests:
                        resp_info = data["params"]["response"]
                        pending_requests[req_id]["status_code"] = resp_info.get("status")
                        pending_requests[req_id]["mime"] = resp_info.get("mimeType")

                # Get body when loading finishes
                elif data.get("method") == "Network.loadingFinished":
                    req_id = data["params"]["requestId"]
                    if req_id in pending_requests:
                        mid = next_id()
                        body_request_map[mid] = req_id
                        await ws.send(json.dumps({
                            "id": mid,
                            "method": "Network.getResponseBody",
                            "params": {"requestId": req_id}
                        }))

                # Process body responses
                elif data.get("id") and data["id"] in body_request_map:
                    req_id = body_request_map[data["id"]]
                    meta = pending_requests.get(req_id, {})
                    if "error" in data:
                        print(f"  Body error for {meta.get('operation','?')}: {data['error']}")
                    elif "result" in data and "body" in data["result"]:
                        body = data["result"]["body"]
                        sha = hashlib.sha256(body.encode()).hexdigest()[:12]
                        fname = f"{label}_{meta.get('operation','unknown')}_{sha}.json"
                        fpath = os.path.join(RESEARCH_DIR, fname)
                        with open(fpath, "w") as f:
                            f.write(body)

                        summary = {"body_bytes": len(body), "path": fpath, "sha256_prefix": sha}
                        try:
                            body_json = json.loads(body)
                            summary["json"] = True
                            summary["top_keys"] = list(body_json.keys())[:5]
                            if meta.get("operation") == "getStoreV1":
                                summary["store_summary"] = summarize_getstore(body_json)
                        except json.JSONDecodeError:
                            summary["json"] = False

                        captured_responses.append({
                            "operation": meta.get("operation"),
                            "url_path": meta.get("url", "").split("ubereats.com")[-1][:80],
                            "status_code": meta.get("status_code"),
                            "mime": meta.get("mime"),
                            "request_keys": meta.get("sanitized", {}).get("postData_keys"),
                            **summary,
                        })
                        op = meta.get("operation", "?")
                        print(f"  CAPTURED {op}: {len(body)} bytes -> {fname}")

            except asyncio.TimeoutError:
                continue

        # Print structured summary
        print(f"\n{'='*60}")
        print(f"CAPTURE SUMMARY: {label}")
        print(f"{'='*60}")
        for r in captured_responses:
            print(f"\nOPERATION: {r.get('operation')}")
            print(f"  STATUS:     {r.get('status_code')}")
            print(f"  MIME:       {r.get('mime')}")
            print(f"  BODY_BYTES: {r.get('body_bytes')}")
            print(f"  JSON:       {r.get('json')}")
            print(f"  TOP_KEYS:   {r.get('top_keys')}")
            print(f"  REQ_KEYS:   {r.get('request_keys')}")
            print(f"  PATH:       {r.get('path')}")
            if r.get("store_summary"):
                ss = r["store_summary"]
                print(f"  STORE_ID:   {ss.get('store_uuid')}")
                print(f"  STORE_NAME: {ss.get('store_title')}")
                print(f"  SECTIONS:   {ss.get('sections_declared')} declared / {ss.get('sections_fetched')} fetched")
                print(f"  ITEMS:      {ss.get('total_items')}")
                print(f"  COMPLETE:   {ss.get('completeness')}")
        print(f"\nTOTAL CAPTURES: {len(captured_responses)}")
        return captured_responses


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.ubereats.com/mx/store/soriana-belenes/UMYErW_lWVOd_FFwOYN1BA"
    label = sys.argv[2] if len(sys.argv) > 2 else "soriana"
    asyncio.run(capture_store(url, label))
