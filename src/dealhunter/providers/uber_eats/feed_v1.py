def parse_feed_v1(feed_data):
    """
    Parses the getFeedV1 JSON response and returns a list of stores in range.
    """
    stores = []
    
    if not feed_data or not feed_data.get("data"):
        return stores
        
    feed = feed_data.get("data", {}).get("feedItems", [])
    
    for item in feed:
        store_info = item.get("store", {})
        if store_info:
            store_uuid = store_info.get("storeUuid")
            store_name = store_info.get("title", {}).get("text")
            if store_uuid and store_name:
                if not any(s["uuid"] == store_uuid for s in stores):
                    stores.append({
                        "uuid": store_uuid,
                        "name": store_name,
                        "type": "market"
                    })
    return stores
