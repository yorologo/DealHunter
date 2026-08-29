import re
with open("src/dealhunter/identity/normalization.py", "r") as f:
    content = f.read()

# Replace the 5% tolerance with strict equivalence.
# Also fix approximation detection.
old_reject_logic = """
    # 4. Total quantity mismatch (tolerance 5%)
    if sig1["total"] and sig2["total"] and sig1["unit"] == sig2["unit"]:
        diff = abs(sig1["total"] - sig2["total"])
        max_val = max(sig1["total"], sig2["total"])
        if max_val > 0 and diff / max_val > 0.05:
             return True, f"Total quantity mismatch ({sig1['total']} vs {sig2['total']})"
"""

new_reject_logic = """
    # 4. Total quantity mismatch (STRICT equivalence)
    if sig1["total"] and sig2["total"] and sig1["unit"] == sig2["unit"]:
        # Allow small floating point variations (e.g. 1.0 vs 1.000001) but not 5%
        if abs(sig1["total"] - sig2["total"]) > 0.001:
             return True, f"Total quantity mismatch ({sig1['total']} vs {sig2['total']})"
"""

content = content.replace(old_reject_logic.strip(), new_reject_logic.strip())

# Add logic for approximate quantities (peso variable)
approx_logic = """
def parse_package(text, qty_val, unit_val):
"""

new_approx_logic = """
def parse_package(text, qty_val, unit_val):
    is_approx = False
    if text:
        text_lower = text.lower()
        if any(w in text_lower for w in ['aprox', 'approximately', 'peso variable', 'variable weight']):
            is_approx = True
"""

content = content.replace(approx_logic.strip(), new_approx_logic.strip())

# Wait, we need to return is_approx in signature? Let's check extract_signature
old_extract = """
def extract_signature(brand, name, qty, unit):
    norm_brand = normalize_text(brand)
    norm_name = normalize_text(name)
    count, per_unit, total, norm_unit = parse_package(name, qty, unit)
"""

new_extract = """
def extract_signature(brand, name, qty, unit):
    norm_brand = normalize_text(brand)
    norm_name = normalize_text(name)
    
    # Re-implemented parse_package locally to include is_approx without changing tuple size in tests if possible
    # Actually, we can just return it in signature dictionary directly
    is_approx = False
    if name:
        text_lower = name.lower()
        if any(w in text_lower for w in ['aprox', 'approximately', 'peso variable', 'variable weight']):
            is_approx = True
            
    count, per_unit, total, norm_unit = parse_package(name, qty, unit)
"""

content = content.replace(old_extract.strip(), new_extract.strip())

old_sig_return = """
    return {
        "brand": norm_brand,
        "base_name": base_name,
        "count": count,
        "per_unit": per_unit,
        "total": total,
        "unit": norm_unit
    }
"""

new_sig_return = """
    return {
        "brand": norm_brand,
        "base_name": base_name,
        "count": count,
        "per_unit": per_unit,
        "total": total,
        "unit": norm_unit,
        "approximate_quantity": is_approx
    }
"""

content = content.replace(old_sig_return.strip(), new_sig_return.strip())


with open("src/dealhunter/identity/normalization.py", "w") as f:
    f.write(content)
