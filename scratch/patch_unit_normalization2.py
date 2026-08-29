import re
with open("src/dealhunter/identity/normalization.py", "r") as f:
    content = f.read()

new_parse_package = """
def parse_package(text, qty_val, unit_val):
    is_approx = False
    if text:
        text_lower = text.lower()
        if any(w in text_lower for w in ['aprox', 'approximately', 'peso variable', 'variable weight']):
            is_approx = True

    count = 1
    per_unit = float(qty_val) if qty_val else None
    unit = str(unit_val).lower().strip() if unit_val else None
    
    def normalize_value(val, u):
        if not val or not u: return val, u
        if u == 'kg': return val * 1000, 'g'
        if u == 'l': return val * 1000, 'ml'
        return val, u
        
    per_unit, unit = normalize_value(per_unit, unit)
    total = per_unit

    if not text:
        return count, per_unit, total, unit

    text_lower = text.lower()
    
    # Try NxM format
    m = re.search(r'(\d+)\s*x\s*([\d\.]+)\s*([a-z]+)', text_lower)
    if m:
        count = int(m.group(1))
        pu = float(m.group(2))
        u = m.group(3)
        pu, u = normalize_value(pu, u)
        return count, pu, count * pu, u
        
    # Try X unidades / Y g format
    m = re.search(r'(\d+)\s*(?:unidades|piezas|pz|pack).*?(?:/|de|con)\s*([\d\.]+)\s*([a-z]+)', text_lower)
    if m:
        count = int(m.group(1))
        t = float(m.group(2))
        u = m.group(3)
        t, u = normalize_value(t, u)
        return count, t / count if count > 0 else t, t, u
        
    m = re.search(r'(\d+)\s*(?:pack|unidades|piezas|pz)', text_lower)
    if m:
        count = int(m.group(1))
        if per_unit and count > 1:
            per_unit = total / count
            
    return count, per_unit, total, unit
"""

content = re.sub(r'def parse_package\(text, qty_val, unit_val\):.*?return count, per_unit, total, unit', lambda m: new_parse_package.strip(), content, flags=re.DOTALL)

with open("src/dealhunter/identity/normalization.py", "w") as f:
    f.write(content)
