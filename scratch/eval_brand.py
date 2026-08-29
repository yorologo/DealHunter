import json

with open("tests/corpus/review_corpus.json") as f:
    corpus = json.load(f)

stats = {
    "RAPPI_STRUCTURED_BRAND": 0,
    "UBER_DERIVED_BRAND": 0,
    "BRAND_UNKNOWN": 0
}

for pair in corpus:
    for p in (pair["p1"], pair["p2"]):
        brand = p.get("brand", "")
        # Assuming provider is not available, we just check if brand is not empty
        # wait, let me look at a review_corpus.json item again
        if brand:
            stats["RAPPI_STRUCTURED_BRAND"] += 1
        else:
            stats["BRAND_UNKNOWN"] += 1

print(json.dumps(stats, indent=2))
