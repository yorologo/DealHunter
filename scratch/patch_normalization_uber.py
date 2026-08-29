import re

with open('src/dealhunter/identity/normalization.py', 'r') as f:
    content = f.read()

patch = """
def extract_signature(brand, name, qty, unit):
    norm_brand = normalize_text(brand)
    
    # Uber title-derived brand (e.g., "Coca-Cola · Refresco")
    if not norm_brand and name and ' · ' in name:
        parts = name.split(' · ', 1)
        if len(parts) == 2:
            derived_brand = parts[0].strip()
            # simple sanity check: if it's too long, maybe not a brand
            if len(derived_brand) < 30:
                norm_brand = normalize_text(derived_brand)
                name = parts[1].strip()

    norm_name = normalize_text(name)
"""

content = content.replace("def extract_signature(brand, name, qty, unit):\n    norm_brand = normalize_text(brand)\n    norm_name = normalize_text(name)", patch)

with open('src/dealhunter/identity/normalization.py', 'w') as f:
    f.write(content)
