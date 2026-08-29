import json
import os

def load_gold_corpus(path="tests/corpus/gold_sample.json"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Gold corpus not found at {path}")
    
    with open(path) as f:
        corpus = json.load(f)
        
    expected_total = 30
    if len(corpus) != expected_total:
        raise ValueError(f"GOLD_RECOVERY = BLOCKED: Expected {expected_total} pairs in gold corpus, but found {len(corpus)}.")
        
    return corpus
