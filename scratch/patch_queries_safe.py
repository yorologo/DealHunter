import re

with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

# Fix config imports
content = content.replace("from dealhunter.query_layer import build_faceted_query", "from dealhunter.query_layer import build_faceted_query\n    from dealhunter.config import get_merged_config\n    from dealhunter.eligibility import EligibilityEngine")
content = content.replace("q, count_q, params = build_faceted_query(facets)", "config = get_merged_config(None)\n    engine = EligibilityEngine(config)\n    q, count_q, params = build_faceted_query(facets, config)")

content = content.replace("from dealhunter.query_layer import get_facet_counts", "from dealhunter.query_layer import get_facet_counts\n    from dealhunter.config import get_merged_config")
content = content.replace("counts = get_facet_counts(conn, facets)", "counts = get_facet_counts(conn, facets, get_merged_config(None))")

# Modify products loop in get_catalog
old_loop = """
    for r in rows:
        products.append({
            "product_id": r[0],
            "store_id": r[1],
            "product_name": r[2],
            "store_name": r[3],
            "store_type": r[4],
            "brand": r[6],
            "category": r[7],
            "current_price": r[8],
            "original_price": r[9],
            "discount_percent": r[10] or 0.0,
            "savings": (r[9] - r[8]) if r[9] and r[8] else 0.0,
            "promotion_type": r[11],
            "promotion_label": r[12],
            "has_pro_offer": r[13],
            "pro_price": r[14],
            "pro_discount_effective": r[15],
            "limit_info": r[16],
            "availability": r[17],
            "ts": r[18],
            "quantity": r[19],
            "unit": r[20],
            "normalized_quantity": r[21],
            "normalized_unit": r[22],
        })
"""

new_loop = """
    for r in rows:
        provider = r[23] if len(r) > 23 else 'rappi'
        has_pro = bool(r[13])
        elig = engine.evaluate(provider, has_pro)
        req_mem = engine.map_offer_to_membership(provider, has_pro)
        
        products.append({
            "product_id": r[0],
            "store_id": r[1],
            "product_name": r[2],
            "store_name": r[3],
            "store_type": r[4],
            "brand": r[6],
            "category": r[7],
            "current_price": r[8],
            "original_price": r[9],
            "discount_percent": r[10] or 0.0,
            "savings": (r[9] - r[8]) if r[9] and r[8] else 0.0,
            "promotion_type": r[11],
            "promotion_label": r[12],
            "has_pro_offer": has_pro,
            "pro_price": r[14],
            "pro_discount_effective": r[15],
            "limit_info": r[16],
            "availability": r[17],
            "ts": r[18],
            "quantity": r[19],
            "unit": r[20],
            "normalized_quantity": r[21],
            "normalized_unit": r[22],
            "provider": provider,
            "ranking_eligible": elig["ranking_eligible"],
            "requires_membership": req_mem,
        })
"""

if old_loop in content:
    content = content.replace(old_loop, new_loop)
else:
    print("WARNING: Could not find old loop")

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(content)

