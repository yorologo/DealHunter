import sys
import json
import sqlite3
import os
import uuid

# Add src to pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dealhunter.db import get_default_db_path
from dealhunter.identity.evaluator import generate_candidates

def main():
    db_path = get_default_db_path()
    candidates = generate_candidates(db_path)
    
    # Sort and take top 600
    candidates = sorted(candidates, key=lambda x: x["confidence"], reverse=True)
    sample = candidates[:600]
    
    review_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests', 'corpus', 'review_corpus.json'))
    matcher_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests', 'corpus', 'matcher_output.json'))
    
    review = []
    matcher = []
    
    for c in sample:
        pair_id = str(uuid.uuid4())
        
        # Blinded corpus for human review
        review.append({
            "pair_id": pair_id,
            "p1": {
                "provider": c["p1"]["provider"],
                "store_id": c["p1"]["store_id"],
                "product_id": c["p1"]["product_id"],
                "display_name": c["p1"]["name"],
                "brand": c["p1"]["brand"],
                "signature": c["p1"]["signature"]
            },
            "p2": {
                "provider": c["p2"]["provider"],
                "store_id": c["p2"]["store_id"],
                "product_id": c["p2"]["product_id"],
                "display_name": c["p2"]["name"],
                "brand": c["p2"]["brand"],
                "signature": c["p2"]["signature"]
            },
            "label": None,
            "reason": None
        })
        
        # Matcher output stored separately
        matcher.append({
            "pair_id": pair_id,
            "confidence": c["confidence"]
        })
        
    with open(review_path, "w") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)
        
    with open(matcher_path, "w") as f:
        json.dump(matcher, f, indent=2, ensure_ascii=False)
        
    print(f"Generated {len(review)} pairs for review at {review_path}")
    print(f"Matcher scores saved separately at {matcher_path}")

if __name__ == "__main__":
    main()
