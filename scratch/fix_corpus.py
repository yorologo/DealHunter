import json
import uuid

with open("tests/corpus/review_corpus.json", "r") as f:
    data = json.load(f)

# The original output was:
# {
#   "p1": "Name | Brand",
#   "p2": "Name | Brand",
#   "confidence": 0.5,
#   "match": None
# }
# We want it to be blinded and structured.

new_data = []
for d in data:
    new_data.append({
        "pair_id": str(uuid.uuid4()),
        "p1": {
            "display_name": d["p1"].split(" | ")[0],
            "brand": d["p1"].split(" | ")[1] if " | " in d["p1"] else "",
        },
        "p2": {
            "display_name": d["p2"].split(" | ")[0],
            "brand": d["p2"].split(" | ")[1] if " | " in d["p2"] else "",
        },
        "label": None,
        "reason": None
    })

with open("tests/corpus/review_corpus.json", "w") as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)

