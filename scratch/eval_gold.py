import json
import sys
sys.path.append("src")
from classifier import classify_pair

with open("tests/corpus/gold_sample.json") as f:
    gold = json.load(f)

results = {"MATCH": {"AUTO_CONFIRMED": 0, "REVIEW_REQUIRED": 0, "REJECTED": 0},
           "NO_MATCH": {"AUTO_CONFIRMED": 0, "REVIEW_REQUIRED": 0, "REJECTED": 0},
           "AMBIGUOUS": {"AUTO_CONFIRMED": 0, "REVIEW_REQUIRED": 0, "REJECTED": 0},
           "total": 0,
           "false_auto_confirmed": 0}

for row in gold:
    # Handle the fact that gold_sample has "match" boolean instead of "label" string
    label_bool = row.get("match", None)
    if label_bool is True:
        label = "MATCH"
    elif label_bool is False:
        label = "NO_MATCH"
    else:
        label = row.get("label", "AMBIGUOUS")
        
    p1 = row["p1"]
    p2 = row["p2"]
    
    status, reason = classify_pair(p1, p2)
    
    if label not in results:
        results[label] = {"AUTO_CONFIRMED": 0, "REVIEW_REQUIRED": 0, "REJECTED": 0}

    results[label][status] += 1
    results["total"] += 1
    if status == "AUTO_CONFIRMED" and label != "MATCH":
        results["false_auto_confirmed"] += 1
        print(f"FALSE POSITIVE: {p1} vs {p2} -> {reason}")

print(json.dumps(results, indent=2))
