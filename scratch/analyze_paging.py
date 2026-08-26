import json, os

RESEARCH_DIR = os.path.expanduser("~/.local/share/DealHunter/research/uber-eats/cdp")

for f in os.listdir(RESEARCH_DIR):
    if "getStoreV1" in f:
        with open(os.path.join(RESEARCH_DIR, f)) as fh:
            data = json.load(fh)
        d = data.get("data", {})
        
        # catalogSectionPagingInfo
        paging = d.get("catalogSectionPagingInfo")
        print("catalogSectionPagingInfo:", json.dumps(paging, indent=2) if paging else "None")
        
        # sectionEntitiesMap
        sem = d.get("sectionEntitiesMap", {})
        print(f"\nsectionEntitiesMap: {len(sem)} keys")
        for k, v in sem.items():
            print(f"  key={k[:16]}... type={type(v).__name__} len={len(v) if isinstance(v, (list,dict)) else '?'}")
        
        # subsectionsMap
        ssm = d.get("subsectionsMap", {})
        print(f"\nsubsectionsMap: {len(ssm)} keys")
        for k, v in ssm.items():
            if isinstance(v, list):
                print(f"  key={k[:16]}... items={len(v)}")
                if v:
                    print(f"    sample keys:", list(v[0].keys())[:5] if isinstance(v[0], dict) else type(v[0]))
            else:
                print(f"  key={k[:16]}... type={type(v).__name__}")
        
        # aisles
        aisles = d.get("aisles", [])
        print(f"\naisles: {len(aisles)}")
        for a in aisles[:5]:
            if isinstance(a, dict):
                print(f"  {a.get('title','?')} items={len(a.get('items',[]))}")
        
        # categories
        cats = d.get("categories", [])
        print(f"\ncategories: {len(cats)}")
        for c in cats[:10]:
            if isinstance(c, dict):
                print(f"  {c.get('name','?')} id={c.get('uuid','?')[:12]}")
            else:
                print(f"  {c}")
        
        # shouldRenderAllItems
        print(f"\nshouldRenderAllItems:", d.get("shouldRenderAllItems"))
