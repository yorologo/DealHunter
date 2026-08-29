import re

with open("src/dealhunter/web/queries.py", "r") as f:
    content = f.read()

# Add provider and eligibility info
replacement = """
    from dealhunter.eligibility import EligibilityEngine
    config = get_merged_config(None)
    engine = EligibilityEngine(config)
    
    q, count_q, params = build_faceted_query(facets, config)
    
    c.execute(count_q, params)
    total = c.fetchone()[0]
    
    c.execute(q, params)
    rows = c.fetchall()
    
    products = []
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
            "timestamp": r[18],
            "quantity": r[19],
            "unit": r[20],
            "normalized_quantity": r[21],
            "normalized_unit": r[22],
            "provider": provider,
            "ranking_eligible": elig["ranking_eligible"],
            "requires_membership": req_mem,
        })
"""

# Find the block from q, count_q to the end of the for loop
import sys
start_str = "q, count_q, params = build_faceted_query(facets, get_merged_config(None))"

# We'll just replace the whole body of get_catalog for safety since regex is tricky with indentation.
def replace_body():
    lines = content.split('\n')
    new_lines = []
    in_catalog = False
    skip_until = None
    for i, line in enumerate(lines):
        if line.startswith("def get_catalog("):
            in_catalog = True
            new_lines.append(line)
            continue
            
        if in_catalog:
            if line.strip() == "q, count_q, params = build_faceted_query(facets, get_merged_config(None))":
                new_lines.append(replacement)
                in_catalog = False
                skip_until = "for i in products:"
            else:
                new_lines.append(line)
        else:
            if skip_until:
                if skip_until in line:
                    skip_until = None
                    new_lines.append(line)
            else:
                new_lines.append(line)
    return '\n'.join(new_lines)

with open("src/dealhunter/web/queries.py", "w") as f:
    f.write(replace_body())
