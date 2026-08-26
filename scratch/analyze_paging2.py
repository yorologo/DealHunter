import json, os

RESEARCH_DIR = os.path.expanduser("~/.local/share/DealHunter/research/uber-eats/cdp")

for f in os.listdir(RESEARCH_DIR):
    if "getStoreV1" in f:
        with open(os.path.join(RESEARCH_DIR, f)) as fh:
            data = json.load(fh)
        d = data.get("data", {})
        
        # catalogSectionPagingInfo — KEY FINDING
        paging = d.get("catalogSectionPagingInfo")
        print("catalogSectionPagingInfo:", json.dumps(paging, indent=2))
        
        # aisles (might be dict not list)
        aisles = d.get("aisles")
        print(f"\naisles type: {type(aisles).__name__}")
        if isinstance(aisles, dict):
            print(f"  keys: {list(aisles.keys())[:5]}")
        elif isinstance(aisles, list):
            print(f"  count: {len(aisles)}")
        
        # categories
        cats = d.get("categories")
        print(f"\ncategories type: {type(cats).__name__}")
        if isinstance(cats, list):
            for c in cats[:10]:
                print(f"  {c}")
        elif isinstance(cats, dict):
            for k in list(cats.keys())[:5]:
                print(f"  {k}: {str(cats[k])[:60]}")
        
        print(f"\nshouldRenderAllItems:", d.get("shouldRenderAllItems"))
        
        # Check sections for hasMore / paging info
        secs = d.get("sections", [])
        for s in secs:
            has_more = {k: v for k, v in s.items() if "more" in k.lower() or "pag" in k.lower() or "offset" in k.lower() or "cursor" in k.lower()}
            if has_more:
                title = s.get("title", "?")
                print(f"\n  section '{title}' paging: {has_more}")
