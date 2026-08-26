import json

with open("scratch/search_res.json") as f:
    data = json.load(f)

for store_id, is_fav in data.get("data", {}).get("favorites", {}).items():
    print(store_id)
