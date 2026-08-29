from dealhunter.identity.normalization import extract_signature, is_hard_reject
from dealhunter.identity.evidence import extract_structured_evidence

def classify_pair(p1, p2):
    sig1 = extract_signature(p1.get("brand", ""), p1.get("name", ""), p1.get("quantity"), p1.get("unit"))
    sig2 = extract_signature(p2.get("brand", ""), p2.get("name", ""), p2.get("quantity"), p2.get("unit"))
    
    ev1 = extract_structured_evidence(p1)
    ev2 = extract_structured_evidence(p2)
    
    rejected, reason = is_hard_reject(sig1, sig2)
    if rejected:
        return "REJECTED", reason
        
    s1_tokens = set(sig1["base_name"].split())
    s2_tokens = set(sig2["base_name"].split())
    
    if not s1_tokens or not s2_tokens:
        return "REVIEW_REQUIRED", "Empty base name"
        
    overlap = len(s1_tokens.intersection(s2_tokens))
    min_len = min(len(s1_tokens), len(s2_tokens))
    max_len = max(len(s1_tokens), len(s2_tokens))
    
    ratio_min = overlap / min_len if min_len > 0 else 0
    ratio_max = overlap / max_len if max_len > 0 else 0
    
    # EXACT EVIDENCE GATE
    # To be AUTO_CONFIRMED, we need known brand, known size, and no prepared foods
    # unless we have exceptional evidence (which we don't for now).
    has_brand = bool(sig1["brand"] and sig2["brand"])
    has_size = bool(sig1["total"] and sig2["total"])
    is_prepared = ev1["is_prepared"] or ev2["is_prepared"]
    
    if ratio_min >= 0.75 and ratio_max >= 0.75:
        if has_brand and has_size and not is_prepared:
            return "AUTO_CONFIRMED", "Exact match with evidence"
        else:
            return "REVIEW_REQUIRED", "Exact similarity but missing critical evidence or is prepared"
        
    if ratio_min >= 0.8:
        return "REVIEW_REQUIRED", "High overlap"
        
    if ratio_min >= 0.5:
        return "REVIEW_REQUIRED", "Moderate overlap"
        
    return "REJECTED", "Low overlap"

