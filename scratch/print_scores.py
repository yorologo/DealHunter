import json
import sys
sys.path.append("src")
from classifier import classify_pair
from dealhunter.identity.normalization import extract_signature

with open("tests/corpus/review_corpus_v2.json") as f:
    corpus = json.load(f)

for pair in corpus[:10]:
    p1 = pair["p1"]
    p2 = pair["p2"]
    
    sig1 = extract_signature(p1.get("brand", ""), p1.get("name", ""), p1.get("quantity"), p1.get("unit"))
    sig2 = extract_signature(p2.get("brand", ""), p2.get("name", ""), p2.get("quantity"), p2.get("unit"))
    
    s1_tokens = set(sig1["base_name"].split())
    s2_tokens = set(sig2["base_name"].split())
    
    overlap = len(s1_tokens.intersection(s2_tokens))
    min_len = min(len(s1_tokens), len(s2_tokens)) if s1_tokens and s2_tokens else 0
    max_len = max(len(s1_tokens), len(s2_tokens)) if s1_tokens and s2_tokens else 0
    
    print(f"{sig1['base_name']} VS {sig2['base_name']}")
    print(f"overlap: {overlap}, min: {min_len}, max: {max_len}")

