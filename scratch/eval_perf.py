import time
import sys
import json
sys.path.append("src")
from dealhunter.identity.evaluator import generate_candidates

start_time = time.time()
try:
    candidates = generate_candidates("rappi-deals.db")
    c_len = len(candidates)
except Exception as e:
    print(f"Error: {e}")
    c_len = 0
end_time = time.time()

perf = {
    "CPG_ELIGIBLE": "unknown",
    "CANDIDATES": c_len,
    "AVG": "unknown",
    "P95": "unknown",
    "TIME": end_time - start_time,
    "RAM": "unknown"
}

with open("research/identity/5f2/performance.json", "w") as f:
    json.dump(perf, f, indent=2)

print(f"Generated {c_len} candidates in {end_time - start_time:.2f}s")
