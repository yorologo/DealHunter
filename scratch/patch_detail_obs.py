with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

content = content.replace("SELECT price, timestamp, original_price, availability, discount_promotion, promotion_type, promotion_label, run_id", "SELECT price, timestamp, original_price, availability, discount_promotion, promotion_type, promotion_label, run_id, has_pro_offer, pro_price, pro_discount_effective")

new_obs_append = """
        obs.append({
            "price": r[0],
            "timestamp": r[1],
            "original_price": r[2],
            "availability": r[3],
            "discount_promotion": r[4],
            "promotion_type": r[5],
            "promotion_label": r[6],
            "run_id": r[7],
            "has_pro_offer": bool(r[8]),
            "pro_price": r[9],
            "pro_discount_effective": r[10],
        })
"""

import re
content = re.sub(r'obs\.append\(\{\s*"price": r\[0\].*?\}\)', new_obs_append.strip(), content, flags=re.DOTALL)

new_p_current = """
        p["has_pro_offer"] = current["has_pro_offer"]
        p["pro_price"] = current["pro_price"]
        p["pro_discount_effective"] = current["pro_discount_effective"]
        
        from dealhunter.eligibility import EligibilityEngine
        from dealhunter.config import get_merged_config
        cfg = get_merged_config(None)
        engine = EligibilityEngine(cfg)
        
        elig = engine.evaluate(p["provider"], p.get("has_pro_offer", False))
        req_mem = engine.map_offer_to_membership(p["provider"], p.get("has_pro_offer", False))
        
        p["ranking_eligible"] = elig["ranking_eligible"]
        p["requires_membership"] = req_mem
        
        # Calculate metrics
"""

content = content.replace("# Calculate metrics", new_p_current.strip() + "\n        # Calculate metrics")

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)
