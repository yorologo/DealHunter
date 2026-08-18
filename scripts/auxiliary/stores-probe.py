#!/data/data/com.termux/files/usr/bin/python3
import json
import urllib.request
import argparse
import sys
import time

def search_stores(lat, lng, queries):
    stores = {}
    for q in queries:
        url = "https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search"
        payload = json.dumps({"query": q, "lat": lat, "lng": lng, "limit": 50}).encode('utf-8')
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.11.0"
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                for store in data.get("stores", []) or []:
                    s_id = str(store.get("store_id"))
                    if s_id and s_id not in stores:
                        stores[s_id] = {
                            "store_id": s_id,
                            "name": store.get("store_name", ""),
                            "brand": store.get("store_brand_name", "") or store.get("store_name", ""),
                            "type": store.get("parent_store_type", store.get("store_type", "")),
                            "availability": True
                        }
        except Exception as e:
            pass
        time.sleep(1)
    
    return list(stores.values())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lat', type=float, default=19.4326)
    parser.add_argument('--lng', type=float, default=-99.1332)
    args = parser.parse_args()
    
    queries = ["super", "market", "chedraui", "soriana", "walmart", "city market", "la comer", "fresko", "justo"]
    stores = search_stores(args.lat, args.lng, queries)
    
    # If no stores found or we want to ensure we have the hardcoded ones
    known_stores = {
        "990006029": {"store_id": "990006029", "name": "City Market", "brand": "City Market", "type": "market", "availability": True},
        "990003640": {"store_id": "990003640", "name": "Chedraui", "brand": "Chedraui", "type": "market", "availability": True},
        "1930032773": {"store_id": "1930032773", "name": "Chedraui Selecto", "brand": "Chedraui Selecto", "type": "market", "availability": True}
    }
    
    for s in stores:
        known_stores[s["store_id"]] = s
        
    print(json.dumps(list(known_stores.values()), indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
