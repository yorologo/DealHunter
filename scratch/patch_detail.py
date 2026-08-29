with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

# Let's find where p is assigned the latest obs data.
import re
match = re.search(r'p\["has_pro_offer"\] = (.*?)\n', content)
if match:
    # we inject eligibility logic below it
    injection = f"""
    from dealhunter.eligibility import EligibilityEngine
    from dealhunter.config import get_merged_config
    cfg = get_merged_config(None)
    engine = EligibilityEngine(cfg)
    
    elig = engine.evaluate(p["provider"], p.get("has_pro_offer", False))
    req_mem = engine.map_offer_to_membership(p["provider"], p.get("has_pro_offer", False))
    
    p["ranking_eligible"] = elig["ranking_eligible"]
    p["requires_membership"] = req_mem
"""
    content = content.replace(match.group(0), match.group(0) + injection)
    
    with open("src/dealhunter/web/queries.py", "w") as f:
        f.write(content)
else:
    print("Could not find has_pro_offer assignment.")
