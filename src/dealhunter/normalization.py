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
        
    # Clean up extra spaces
    normalized_name = re.sub(r'\s+', ' ', normalized_name)
    
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
    brand = (brand or "").strip()
    name = (normalized_name or "").strip()
    
    # Clean up name: remove special chars, extra spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    # if brand is in name, maybe we don't duplicate it in fingerprint, but for now just concat
    parts = []
    if brand:
        parts.append(brand.lower())
    
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
