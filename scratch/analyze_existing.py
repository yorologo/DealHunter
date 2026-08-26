import json
with open("scratch/soriana_getstore.json") as f:
    data = json.load(f)
d = data.get("data", {})
print("status:", data.get("status"))
print("uuid:", d.get("uuid"))
print("title:", d.get("title"))
print("isOpen:", d.get("isOpen"))
print("sections:", len(d.get("sections", [])))
print("catalogSectionsMap keys:", len(d.get("catalogSectionsMap", {})))
total = 0
for k, v in d.get("catalogSectionsMap", {}).items():
    for el in v:
        if el.get("type") in ("VERTICAL_GRID","HORIZONTAL_GRID"):
            items = el.get("payload",{}).get("standardItemsPayload",{}).get("catalogItems",[])
            total += len(items)
print("total items:", total)
secs = d.get("sections",[])
for s in secs[:10]:
    title = s.get("title",{}).get("text","?")
    print("  sec:", title)
