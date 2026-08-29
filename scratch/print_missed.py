import json
import sys
sys.path.append("src")
from classifier import classify_pair

with open("tests/corpus/review_corpus_v2.json") as f:
    corpus = json.load(f)

# Merge model labels
all_results = []
for i in range(6):
    try:
        with open(f'research/identity/5f2/batch_v2_{i:03d}_results.json') as f:
            content = f.read().strip()
            if content.startswith("```json"): content = content[7:-3]
            all_results.extend(json.loads(content))
    except: pass

labels_by_pair = {r["pair_id"]: r["label"] for r in all_results}

for pair in corpus:
    pair_id = pair["pair_id"]
    p1 = pair["p1"]
    p2 = pair["p2"]
    status, reason = classify_pair(p1, p2)
    model_label = labels_by_pair.get(pair_id, "AMBIGUOUS")
    
    if status == "REVIEW_REQUIRED" and model_label == "EXACT_PRODUCT":
        print(f"MISSED: {p1.get('name')} vs {p2.get('name')}")
        
