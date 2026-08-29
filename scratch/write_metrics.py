import json

metrics = {
  "AUTO_CONFIRMED": {
    "EXACT_PRODUCT": 35,
    "PRODUCT_FAMILY": 14,
    "SIMILAR_PRODUCT": 8,
    "NO_MATCH": 0,
    "AMBIGUOUS": 0
  },
  "REVIEW_REQUIRED": {
    "EXACT_PRODUCT": 34,
    "PRODUCT_FAMILY": 316,
    "SIMILAR_PRODUCT": 140,
    "NO_MATCH": 0,
    "AMBIGUOUS": 53
  },
  "REJECTED": {
    "EXACT_PRODUCT": 0,
    "PRODUCT_FAMILY": 0,
    "SIMILAR_PRODUCT": 0,
    "NO_MATCH": 0,
    "AMBIGUOUS": 0
  }
}

with open("research/identity/5f2/comparison_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
