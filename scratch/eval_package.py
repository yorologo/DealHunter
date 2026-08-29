import json
import sys
sys.path.append("src")
from dealhunter.identity.normalization import parse_package

with open("tests/corpus/review_corpus.json") as f:
    corpus = json.load(f)

stats = {
    "PACK_EXPLICIT": 0,
    "PACK_DERIVED": 0, # not really distinct in this parser
    "SIZE_EXPLICIT": 0,
    "SIZE_DERIVED": 0,
    "SIZE_UNKNOWN": 0,
    "APPROXIMATE": 0,
    "VARIABLE_WEIGHT": 0
}

for pair in corpus:
    for p in (pair["p1"], pair["p2"]):
        name = p.get("display_name", p.get("name", ""))
        qty = p.get("quantity")
        unit = p.get("unit")
        
        count, pu, total, u = parse_package(name, qty, unit)
        
        if count > 1:
            stats["PACK_EXPLICIT"] += 1
            
        if qty and unit:
            stats["SIZE_EXPLICIT"] += 1
        elif total and u:
            stats["SIZE_DERIVED"] += 1
        else:
            stats["SIZE_UNKNOWN"] += 1
            
        name_lower = name.lower()
        if "aprox" in name_lower or "approx" in name_lower:
            stats["APPROXIMATE"] += 1
        if "peso variable" in name_lower or "variable weight" in name_lower:
            stats["VARIABLE_WEIGHT"] += 1

print(json.dumps(stats, indent=2))
