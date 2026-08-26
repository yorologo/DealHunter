import json
with open("scratch/soriana_getstore.json") as f:
    data = json.load(f)
d = data.get("data", {})
print("status:", data.get("status"))
print("uuid:", d.get("uuid"))
print("title:", d.get("title"))
print("isOpen:", d.get("isOpen"))
secs = d.get("sections",[])
print("sections:", len(secs))
for s in secs:
    if isinstance(s, dict):
        title_obj = s.get("title", {})
        if isinstance(title_obj, dict):
            print("  sec:", title_obj.get("text","?"))
        else:
            print("  sec:", title_obj)
    else:
        print("  sec(raw):", str(s)[:60])
csm = d.get("catalogSectionsMap", {})
print("catalogSectionsMap keys:", len(csm))
total = 0
for k, v in csm.items():
    for el in v:
        el_type = el.get("type")
        if el_type in ("VERTICAL_GRID","HORIZONTAL_GRID"):
            sp = el.get("payload",{}).get("standardItemsPayload",{})
            cat = sp.get("title",{}).get("text","?") if isinstance(sp.get("title"), dict) else sp.get("title","?")
            items = sp.get("catalogItems",[])
            total += len(items)
            print("  cat:", cat, "items:", len(items))
print("total items:", total)
print()
# Check if this was PARTIAL (only 1 section fetched vs 7 declared)
print("COMPLETENESS:", "PARTIAL" if len(csm) < len(secs) else "COMPLETE")
