import re

def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
    m = re.search(r'(\d+)\s*x\s*(\d+[\d\.,]*)\s*([a-z]+)', text_lower)
    if m:
        count = int(m.group(1))
        pu = float(m.group(2).replace(',', '.'))
        u = m.group(3)
        pu, u = normalize_value(pu, u)
        return count, pu, count * pu, u
        
    # Try 12 pack 355 ml
    m = re.search(r'(\d+)\s*(?:pack|unidades|piezas|pz).*?(\d+[\d\.,]*)\s*([a-z]+)', text_lower)
    if m:
        count = int(m.group(1))
        pu = float(m.group(2).replace(',', '.'))
        u = m.group(3)
        pu, u = normalize_value(pu, u)
        return count, pu, count * pu, u
        
    # Try X unidades / Y g format (8 und / 340 g)
    m = re.search(r'(\d+)\s*(?:unidades|piezas|pz|pack|und).*?(?:/|de|con)\s*(\d+[\d\.,]*)\s*([a-z]+)', text_lower)
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
        m = re.search(r'(?<!x\s)(?<!\dx)\b(\d+[\d\.,]*)\s*(ml|l|g|kg|oz|lb)\b', text_lower)
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

    
    # Re-implemented parse_package locally to include is_approx without changing tuple size in tests if possible
    # Actually, we can just return it in signature dictionary directly
    is_approx = False
    if name:
        text_lower = name.lower()
        if any(w in text_lower for w in ['aprox', 'approximately', 'peso variable', 'variable weight']):
            is_approx = True
            
    count, per_unit, total, norm_unit = parse_package(name, qty, unit)
    
    # Signature: normalized base name + package signature
    # Remove brand from name if present to get base name
    base_name = norm_name
    if norm_brand and base_name.startswith(norm_brand):
        base_name = base_name[len(norm_brand):].strip()
        
    return {
        "brand": norm_brand,
        "base_name": base_name,
        "count": count,
        "per_unit": per_unit,
        "total": total,
        "unit": norm_unit,
        "approximate_quantity": is_approx
    }

def is_hard_reject(sig1, sig2):
    """
    Returns True if signatures are strictly incompatible.
    """
    # 1. Brand mismatch (if both exist and are different)
    if sig1["brand"] and sig2["brand"]:
        if sig1["brand"] != sig2["brand"]:
            # Check if one is substring of other (e.g. coca cola vs coca)
            if sig1["brand"] not in sig2["brand"] and sig2["brand"] not in sig1["brand"]:
                return True, "Brand mismatch"
                
    # 2. Package incompatibility
    # E.g. 1 L vs 12 x 1 L -> count mismatch
    if sig1["count"] and sig2["count"]:
        if sig1["count"] != sig2["count"]:
            return True, f"Count mismatch ({sig1['count']} vs {sig2['count']})"
            
    # 3. Unit incompatibility (if both exist)
    if sig1["unit"] and sig2["unit"]:
        u1 = sig1["unit"]
        u2 = sig2["unit"]
        # simple unit match (ignoring volume/mass equivalence for now)
        if u1 != u2:
            vol_units = ['ml', 'l']
            mass_units = ['g', 'kg']
            if (u1 in vol_units and u2 not in vol_units) or (u2 in vol_units and u1 not in vol_units):
                return True, f"Unit category mismatch ({u1} vs {u2})"
                
    # 4. Total quantity mismatch (STRICT equivalence)
    if sig1["total"] and sig2["total"] and sig1["unit"] == sig2["unit"]:
        # Allow small floating point variations (e.g. 1.0 vs 1.000001) but not 5%
        if abs(sig1["total"] - sig2["total"]) > 0.001:
             return True, f"Total quantity mismatch ({sig1['total']} vs {sig2['total']})"
             
    return False, ""
