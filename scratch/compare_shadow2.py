import json
import sys
sys.path.append("src")
from classifier import classify_pair

with open("tests/corpus/review_corpus.json") as f:
    corpus = json.load(f)
    
with open("research/identity/5f2/model_labels.json") as f:
    model_labels = json.load(f)

labels_by_pair = {r["pair_id"]: r["label"] for r in model_labels}

review_queue = []

for pair in corpus:
    pair_id = pair["pair_id"]
    p1 = pair["p1"]
    p2 = pair["p2"]
    
    p1_name = p1.get("display_name", p1.get("name", ""))
    p2_name = p2.get("display_name", p2.get("name", ""))
    p1_obj = {"name": p1_name, "brand": p1.get("brand", ""), "quantity": p1.get("quantity"), "unit": p1.get("unit")}
    p2_obj = {"name": p2_name, "brand": p2.get("brand", ""), "quantity": p2.get("quantity"), "unit": p2.get("unit")}
    
    status, reason = classify_pair(p1_obj, p2_obj)
    model_label = labels_by_pair.get(pair_id, "AMBIGUOUS")
    
    # Prioritize for human review
    priority = 0
    if status == "AUTO_CONFIRMED":
        if model_label != "EXACT_PRODUCT":
            priority = 1 # Disagreement!
        else:
            priority = 2 # Audit AUTO_CONFIRMED
    elif status == "REVIEW_REQUIRED" and model_label == "EXACT_PRODUCT":
        priority = 3
        
    if priority > 0:
        review_queue.append({
            "pair_id": pair_id,
            "p1": p1,
            "p2": p2,
            "model_label": model_label,
            "shadow_status": status,
            "shadow_reason": reason,
            "priority": priority
        })

# Sort by priority (1 highest, then 2, 3)
review_queue.sort(key=lambda x: x["priority"])

with open("research/identity/5f2/review_queue.json", "w") as f:
    json.dump(review_queue, f, indent=2)

print(f"Added {len(review_queue)} items to review queue.")
