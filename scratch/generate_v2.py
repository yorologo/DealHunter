import json
import sqlite3
import random
import sys
sys.path.append("src")
from dealhunter.identity.evaluator import generate_candidates
from dealhunter.identity.normalization import extract_signature

print("Generating candidates...")
candidates = generate_candidates("rappi-deals.db")

print(f"Filtering {len(candidates)} candidates for v2 corpus...")
# We want to sample across confidence buckets
high = []
mid = []
low = []

for c in candidates:
    # Ensure they have valid base signatures to be interesting
    p1 = c["p1"]
    p2 = c["p2"]
    if not p1["brand"] and not p2["brand"]:
        continue
    conf = c["confidence"]
    if conf >= 0.8:
        high.append(c)
    elif conf >= 0.6:
        mid.append(c)
    else:
        low.append(c)

random.seed(42)
sampled = []
sampled.extend(random.sample(high, min(300, len(high))))
sampled.extend(random.sample(mid, min(150, len(mid))))
sampled.extend(random.sample(low, min(150, len(low))))

corpus_v2 = []
for c in sampled:
    p1 = c["p1"]
    p2 = c["p2"]
    # We store the raw product for the review corpus
    corpus_v2.append({
        "pair_id": f"{p1['provider']}-{p1['product_id']}-vs-{p2['provider']}-{p2['product_id']}",
        "p1": p1,
        "p2": p2,
        "label": None,
        "reason": None
    })

with open("tests/corpus/review_corpus_v2.json", "w") as f:
    json.dump(corpus_v2, f, indent=2)

print(f"Saved {len(corpus_v2)} pairs to corpus_v2")
