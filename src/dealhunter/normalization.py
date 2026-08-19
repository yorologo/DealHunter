import re

UNIT_MAP = {
    'g': 'g',
    'kg': 'kg',
    'ml': 'ml',
    'l': 'L',
    'pz': 'pieza',
    'pza': 'pieza',
    'pzas': 'pieza',
    'pieza': 'pieza',
    'piezas': 'pieza',
    'tableta': 'tableta',
    'tabletas': 'tableta',
    'cápsula': 'cápsula',
    'cápsulas': 'cápsula',
    'capsula': 'cápsula',
    'capsulas': 'cápsula',
    'pack': 'pack'
}

import unicodedata

def canonicalize_text(text):
    if not text: return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_product_name(name, raw_brand=None):
    if not name:
        return {"normalized_name": "", "brand": raw_brand or "", "quantity": None, "unit": None, "normalized_quantity": None, "normalized_unit": None}
        
    name = name.strip()
    
    # Extract pack first if it exists (e.g. 6 pack 355 ml)
    pack_match = re.search(r'\b(\d+)\s*[-]*\s*pack(?:\s+(\d+(?:\.\d+)?)\s*(ml|l|g|kg))?\b', name, re.IGNORECASE)
    
    quantity = None
    unit = None
    
    if pack_match:
        qty_pack = float(pack_match.group(1))
        qty_sub = pack_match.group(2)
        unit_sub = pack_match.group(3)
        
        if qty_sub and unit_sub:
            unit_sub_lower = unit_sub.lower()
            quantity = qty_pack * float(qty_sub)
            unit = UNIT_MAP.get(unit_sub_lower, unit_sub_lower)
        else:
            quantity = qty_pack
            unit = 'pack'
    else:
        # standard extraction: e.g. "2.5 kg" or "500 ml" or "2 L"
        # also match pieces, etc.
        pattern = r'\b(\d+(?:\.\d+)?)\s*(kg|g|mg|l|ml|pz|pza|pzas|pieza|piezas|tabletas|tableta|cápsulas|cápsula|capsulas|capsula)\b'
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            quantity = float(match.group(1))
            raw_u = match.group(2).lower()
            unit = UNIT_MAP.get(raw_u, raw_u)
            
    # Remove the matched quantity from name to get a cleaner normalized name
    normalized_name = name.lower()
    if pack_match:
        normalized_name = normalized_name.replace(pack_match.group(0).lower(), '').strip()
    elif match:
        normalized_name = normalized_name.replace(match.group(0).lower(), '').strip()
        
    normalized_name = canonicalize_text(normalized_name)
    
    # Normalize quantity/unit
    normalized_quantity = quantity
    normalized_unit = unit
    
    if unit == 'g' and quantity >= 1000:
        normalized_quantity = quantity / 1000.0
        normalized_unit = 'kg'
    elif unit == 'g' and quantity is not None:
        normalized_quantity = quantity / 1000.0
        normalized_unit = 'kg'
    elif unit == 'ml' and quantity is not None:
        normalized_quantity = quantity / 1000.0
        normalized_unit = 'L'
    elif unit == 'mg' and quantity is not None:
        normalized_quantity = quantity / 1000000.0
        normalized_unit = 'kg'

    brand = (raw_brand or "").lower().strip()
    
    return {
        "brand": brand,
        "normalized_name": normalized_name,
        "quantity": quantity,
        "unit": unit,
        "normalized_quantity": normalized_quantity,
        "normalized_unit": normalized_unit
    }

def calculate_unit_price(price, normalized_quantity):
    if price is None or normalized_quantity is None or normalized_quantity <= 0:
        return None
    return round(price / normalized_quantity, 2)

def generate_fingerprint(brand, normalized_name, normalized_quantity, normalized_unit):
    brand = canonicalize_text(brand)
    name = canonicalize_text(normalized_name)
    
    # if brand is in name, maybe we don't duplicate it in fingerprint, but for now just concat
    parts = []
    if brand:
        parts.append(brand.replace(' ', '-'))
    
    # we don't want the quantity in the name if we are using it explicitly. 
    # But doing that perfectly is hard. Just use base name
    if name:
        parts.append(name.replace(' ', '-'))
        
    if normalized_quantity is not None and normalized_unit:
        qty_str = f"{normalized_quantity:g}"
        parts.append(qty_str)
        parts.append(normalized_unit.lower())
        
    if not parts:
        return "unknown"
        
    return "|".join(parts)

def compute_match(p1, p2):
    """
    Returns tuple: (match_type, match_confidence)
    match_type in ("EXACT_MATCH", "HIGH_CONFIDENCE_MATCH", "NO_MATCH")
    p1 and p2 should be dictionaries with normalized fields or directly from products db.
    """
    fp1 = p1.get("fingerprint")
    fp2 = p2.get("fingerprint")
    
    if fp1 and fp2 and fp1 == fp2 and fp1 != "unknown":
        return "EXACT_MATCH", 1.00

    brand1 = canonicalize_text(p1.get("brand", ""))
    brand2 = canonicalize_text(p2.get("brand", ""))
    
    name1 = canonicalize_text(p1.get("normalized_name", ""))
    name2 = canonicalize_text(p2.get("normalized_name", ""))
    
    q1 = p1.get("normalized_quantity")
    q2 = p2.get("normalized_quantity")
    
    u1 = p1.get("normalized_unit")
    u2 = p2.get("normalized_unit")
    
    # 3. No mezclar tamaños
    if q1 is not None and q2 is not None:
        if q1 != q2 or u1 != u2:
            return "NO_MATCH", 0.0
            
    if q1 is None and q2 is not None:
        return "NO_MATCH", 0.0
        
    if q1 is not None and q2 is None:
        return "NO_MATCH", 0.0

    # If brand differs, NO_MATCH
    if brand1 and brand2 and brand1 != brand2:
        return "NO_MATCH", 0.0

    # HIGH CONFIDENCE MATCH check
    words1 = set(name1.split())
    words2 = set(name2.split())
    
    # remove brand from words if present
    if brand1:
        words1 -= set(brand1.split())
        words2 -= set(brand1.split())
        
    if brand2:
        words1 -= set(brand2.split())
        words2 -= set(brand2.split())

    conflicts = [
        {"zero", "light", "original", "clasica", "clasico", "sin", "diet"},
        {"entera", "deslactosada", "light", "semi", "almendra", "soya"},
        {"shampoo", "acondicionador", "crema", "jabon"}
    ]
    
    for conflict_group in conflicts:
        w1_has = words1.intersection(conflict_group)
        w2_has = words2.intersection(conflict_group)
        if w1_has and w2_has and w1_has != w2_has:
            return "NO_MATCH", 0.0
            
    if words1.issubset(words2) or words2.issubset(words1):
        if words1 or words2:
            return "HIGH_CONFIDENCE_MATCH", 0.80

    # overlap ratio
    intersection = words1.intersection(words2)
    if intersection:
        if len(intersection) / max(len(words1), len(words2)) >= 0.5:
             return "HIGH_CONFIDENCE_MATCH", 0.70

    return "NO_MATCH", 0.0

