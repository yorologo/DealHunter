import json, os

RESEARCH_DIR = os.path.expanduser("~/.local/share/DealHunter/research/uber-eats/cdp")

# Find the getStoreV1 capture
for f in os.listdir(RESEARCH_DIR):
    if "getStoreV1" in f:
        path = os.path.join(RESEARCH_DIR, f)
        with open(path) as fh:
            data = json.load(fh)
        d = data.get("data", {})
        print(f"=== {f} ===")
        print("uuid:", d.get("uuid"))
        print("title:", d.get("title"))
        print("isOpen:", d.get("isOpen"))
        
        # Sections analysis
        secs = d.get("sections", [])
        print(f"\nSECTIONS DECLARED: {len(secs)}")
        for i, s in enumerate(secs):
            uuid = s.get("uuid", "?")
            title = s.get("title", "?")
            print(f"  [{i}] uuid={uuid[:12]}... title={title}")
        
        # CatalogSectionsMap analysis
        csm = d.get("catalogSectionsMap", {})
        print(f"\nCATALOG SECTIONS MAP: {len(csm)} keys")
        for k, elements in csm.items():
            print(f"  key={k[:12]}... elements={len(elements)}")
            for el in elements:
                el_type = el.get("type")
                if el_type in ("VERTICAL_GRID", "HORIZONTAL_GRID"):
                    sp = el.get("payload", {}).get("standardItemsPayload", {})
                    title_obj = sp.get("title", {})
                    cat = title_obj.get("text", "?") if isinstance(title_obj, dict) else str(title_obj)
                    items = sp.get("catalogItems", [])
                    print(f"    type={el_type} cat={cat} items={len(items)}")
                    # Sample first item
                    if items:
                        it = items[0]
                        print(f"      sample: {it.get('title','?')[:40]} price={it.get('price')} soldOut={it.get('isSoldOut')}")
                else:
                    print(f"    type={el_type}")
        
        # Check for pagination/cursor hints
        print(f"\npaginationInfo:", d.get("paginationInfo"))
        print("hasMoreSections:", d.get("hasMoreSections"))
        print("nextOffset:", d.get("nextOffset"))
        
        # Check top-level keys for lazy hints
        lazy_keys = [k for k in d.keys() if "page" in k.lower() or "cursor" in k.lower() or "offset" in k.lower() or "more" in k.lower() or "next" in k.lower() or "lazy" in k.lower()]
        print("lazy-related keys:", lazy_keys)
        
        # All top-level keys
        print("\nALL TOP-LEVEL DATA KEYS:", sorted(d.keys()))

# Also check getCatalogPresentationV2
for f in os.listdir(RESEARCH_DIR):
    if "getCatalogPresentation" in f:
        path = os.path.join(RESEARCH_DIR, f)
        with open(path) as fh:
            data = json.load(fh)
        print(f"\n=== {f} ===")
        print(json.dumps(data, indent=2)[:500])
