import json
import os

class GoldRecoveryBlocked(Exception):
    pass

def load_gold_corpus(path="tests/corpus/gold_sample.json"):
    if not os.path.exists(path):
        raise GoldRecoveryBlocked(f"GOLD_RECOVERY = BLOCKED: Gold corpus not found at {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            corpus = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gold corpus at {path} is malformed JSON: {e}")

    if not isinstance(corpus, list):
        raise ValueError(f"Gold corpus at {path} must be a JSON array.")

    expected_total = 30
    if len(corpus) != expected_total:
        raise ValueError(f"Expected {expected_total} pairs in gold corpus, but found {len(corpus)}.")

    return corpus
