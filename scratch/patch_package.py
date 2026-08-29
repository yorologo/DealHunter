import re

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
    
    # Check 10+2 format (promotional extra)
    m = re.search(r'(\d+)\+(\d+)\s*(?:sobres|piezas|pz|pack|unidades)', text_lower)
    if m:
        count = int(m.group(1)) + int(m.group(2))
        return count, per_unit, total, unit

    # Try NxM format (8 x 42.5 g)
    m = re.search(r'(\d+)\s*x\s*([\d\.,]+)\s*([a-z]+)', text_lower)
    if m:
        count = int(m.group(1))
        pu = float(m.group(2).replace(',', '.'))
        u = m.group(3)
        pu, u = normalize_value(pu, u)
        return count, pu, count * pu, u
        
    # Try 12 pack 355 ml
    m = re.search(r'(\d+)\s*(?:pack|unidades|piezas|pz).*?([\d\.,]+)\s*([a-z]+)', text_lower)
    if m:
        count = int(m.group(1))
        pu = float(m.group(2).replace(',', '.'))
        u = m.group(3)
        pu, u = normalize_value(pu, u)
        return count, pu, count * pu, u
        
    # Try X unidades / Y g format (8 und / 340 g)
    m = re.search(r'(\d+)\s*(?:unidades|piezas|pz|pack|und).*?(?:/|de|con)\s*([\d\.,]+)\s*([a-z]+)', text_lower)
    if m:
        count = int(m.group(1))
        t = float(m.group(2).replace(',', '.'))
        u = m.group(3)
        t, u = normalize_value(t, u)
        return count, t / count if count > 0 else t, t, u

    # Simple pack size (4 piezas)
    m = re.search(r'(\d+)\s*(?:pack|unidades|piezas|pz|sobres)', text_lower)
    if m:
        count = int(m.group(1))
        if per_unit and count > 1:
            per_unit = total / count
        # Don't return yet, we might still extract simple qty if unit is missing
        # Actually if unit is missing, we just use what we have
        if per_unit and unit:
            return count, per_unit, total, unit

    # Simple quantity without count (600 ml, 1.2 L bottle, 1,5 L, 1 kg)
    # Check if total is not set yet
    if not total or not unit:
        # Match standalone number + unit
        # careful with stuff like "coca cola zero", it has no number.
        m = re.search(r'(?<!x\s)(?<!\dx)\b([\d\.,]+)\s*(ml|l|g|kg|oz|lb)\b', text_lower)
        if m:
            t_val = float(m.group(1).replace(',', '.'))
            u_val = m.group(2)
            t_val, u_val = normalize_value(t_val, u_val)
            if not unit:
                unit = u_val
            if not total:
                total = t_val
                if count > 0:
                    per_unit = total / count
            
    return count, per_unit, total, unit

