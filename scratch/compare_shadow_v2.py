import json
import sys
import os
sys.path.append("src")
from classifier import classify_pair

with open("tests/corpus/review_corpus_v2.json") as f:
    corpus = json.load(f)

# Merge model labels
all_results = []
for i in range(6):
    file_path = f'research/identity/5f2/batch_v2_{i:03d}_results.json'
    if os.path.exists(file_path):
        try:
            with open(file_path) as f:
                content = f.read().strip()
                if content.startswith("```json"):
                    content = content[7:-3]
                all_results.extend(json.loads(content))
        except Exception as e:
            print(f"Failed {file_path}: {e}")

labels_by_pair = {r["pair_id"]: r["label"] for r in all_results}

results = {
    "AUTO_CONFIRMED": {"EXACT_PRODUCT": 0, "PRODUCT_FAMILY": 0, "SIMILAR_PRODUCT": 0, "NO_MATCH": 0, "AMBIGUOUS": 0},
    "REVIEW_REQUIRED": {"EXACT_PRODUCT": 0, "PRODUCT_FAMILY": 0, "SIMILAR_PRODUCT": 0, "NO_MATCH": 0, "AMBIGUOUS": 0},
    "REJECTED": {"EXACT_PRODUCT": 0, "PRODUCT_FAMILY": 0, "SIMILAR_PRODUCT": 0, "NO_MATCH": 0, "AMBIGUOUS": 0},
}
hard_conflict_count = 0
disagreements = []

for pair in corpus:
    pair_id = pair["pair_id"]
    p1 = pair["p1"]
    p2 = pair["p2"]
    
    status, reason = classify_pair(p1, p2)
    
    model_label = labels_by_pair.get(pair_id, "AMBIGUOUS")
    if model_label not in results[status]:
        results[status][model_label] = 0
    results[status][model_label] += 1
    
    if status == "AUTO_CONFIRMED" and model_label != "EXACT_PRODUCT":
        disagreements.append((p1, p2, model_label, reason))

print(json.dumps(results, indent=2))
print(f"False AUTO_CONFIRMED: {len(disagreements)}")
for d in disagreements[:5]:
    print(f"  {d[2]}: {d[0]['name']} vs {d[1]['name']} ({d[3]})")
