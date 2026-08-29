import json
import sys
import os
sys.path.append("src")
from classifier import classify_pair

with open("tests/corpus/review_corpus.json") as f:
    corpus = json.load(f)
    
with open("research/identity/5f2/model_labels.json") as f:
    model_labels = json.load(f)

# Map pair_id to model label
labels_by_pair = {r["pair_id"]: r["label"] for r in model_labels}

results = {
    "AUTO_CONFIRMED": {"EXACT_PRODUCT": 0, "PRODUCT_FAMILY": 0, "SIMILAR_PRODUCT": 0, "NO_MATCH": 0, "AMBIGUOUS": 0},
    "REVIEW_REQUIRED": {"EXACT_PRODUCT": 0, "PRODUCT_FAMILY": 0, "SIMILAR_PRODUCT": 0, "NO_MATCH": 0, "AMBIGUOUS": 0},
    "REJECTED": {"EXACT_PRODUCT": 0, "PRODUCT_FAMILY": 0, "SIMILAR_PRODUCT": 0, "NO_MATCH": 0, "AMBIGUOUS": 0},
}
hard_conflict_count = 0

for pair in corpus:
    pair_id = pair["pair_id"]
    p1 = pair["p1"]
    p2 = pair["p2"]
    
    # Extract properties (handling different keys)
    p1_name = p1.get("display_name", p1.get("name", ""))
    p2_name = p2.get("display_name", p2.get("name", ""))
    p1_obj = {"name": p1_name, "brand": p1.get("brand", ""), "quantity": p1.get("quantity"), "unit": p1.get("unit")}
    p2_obj = {"name": p2_name, "brand": p2.get("brand", ""), "quantity": p2.get("quantity"), "unit": p2.get("unit")}
    
    status, reason = classify_pair(p1_obj, p2_obj)
    
    if status == "AUTO_CONFIRMED":
        # Rule 12. Hard-conflict recheck. We already did is_hard_reject inside classify_pair. 
        pass
        
    model_label = labels_by_pair.get(pair_id, "AMBIGUOUS")
    if model_label not in results[status]:
        results[status][model_label] = 0
    results[status][model_label] += 1

print(json.dumps(results, indent=2))
