def extract_structured_evidence(raw_product_dict):
    """
    Extracts structured evidence from a raw product dictionary.
    Since we don't have schema v16 yet, we'll do this in-memory.
    """
    provider = raw_product_dict.get("provider", "")
    evidence = {
        "brand": raw_product_dict.get("brand", ""),
        "category": raw_product_dict.get("category", ""),
        "is_prepared": False,
        "is_fresh": False,
        "external_ids": {}
    }
    
    # Simple heuristic for prepared/fresh based on category or tags if available
    # For now, if we see restaurant typical words, we flag it.
    name = raw_product_dict.get("name", "").lower()
    if any(w in name for w in ["taco", "chilaquiles", "torta", "lonche", "hamburguesa", "pizza"]):
        evidence["is_prepared"] = True
        
    return evidence

