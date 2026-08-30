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
            
            # Attempt to classify from structured payload evidence
            store_type_raw = store_info.get("storeType", "")
            action_url = store_info.get("actionUrl", "")
            
            if store_type_raw == "RESTAURANT" or "/restaurant/" in action_url:
                classified_type = "restaurant"
            elif store_type_raw == "GROCERY" or "/grocery/" in action_url:
                classified_type = "grocery"
            else:
                classified_type = "unknown"
                
            if store_uuid and store_name:
                if not any(s["uuid"] == store_uuid for s in stores):
                    stores.append({
                        "uuid": store_uuid,
                        "name": store_name,
                        "type": classified_type
                    })
    return stores
