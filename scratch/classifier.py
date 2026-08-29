from dealhunter.identity.normalization import extract_signature, is_hard_reject

def classify_pair(p1, p2):
    sig1 = extract_signature(p1.get("brand", ""), p1.get("name", ""), p1.get("quantity"), p1.get("unit"))
    sig2 = extract_signature(p2.get("brand", ""), p2.get("name", ""), p2.get("quantity"), p2.get("unit"))
    
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
    
    # Heuristics for AUTO_CONFIRMED: high token overlap (e.g. 1.0)
    # Plus exact brand match, plus exact size match (which is verified by not rejected)
    if ratio_max == 1.0:
        return "AUTO_CONFIRMED", "Exact match"
        
    if ratio_min >= 0.8:
        return "REVIEW_REQUIRED", "High overlap"
        
    if ratio_min >= 0.5:
        return "REVIEW_REQUIRED", "Moderate overlap"
        
    return "REJECTED", "Low overlap"

