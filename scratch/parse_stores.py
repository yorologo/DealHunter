import json

with open("scratch/search_res.json") as f:
    data = json.load(f)

# The response probably has a feed items array or store map. Let's find "storeUuid" keys
def find_stores(obj, res):
    if isinstance(obj, dict):
        if "storeUuid" in obj:
            res.add((obj["storeUuid"], obj.get("title", {}).get("text", "Unknown")))
        for k, v in obj.items():
            find_stores(v, res)
    elif isinstance(obj, list):
        for item in obj:
            find_stores(item, res)

res = set()
find_stores(data, res)
for r in list(res)[:10]:
    print(r)
