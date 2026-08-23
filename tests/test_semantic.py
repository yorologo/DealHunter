from dealhunter.semantic import classify_membership, CATEGORY, COLLECTION, UNKNOWN, normalize_name

def test_normalize_name():
    assert normalize_name("  Ofertas  Pro ") == "ofertas pro"
    assert normalize_name("BEBIDAS") == "bebidas"
    assert normalize_name(" ") == ""
    assert normalize_name(None) == ""

def test_provider_category_exact_match():
    # If the product's official category matches the container exactly
    res, reason = classify_membership("Bebidas", "Bebidas", "provider")
    assert res == CATEGORY
    assert reason == "matches_provider_category"

def test_inferred_category_match_is_unknown():
    # Inferred categories are NOT ground truth for this classifier
    res, reason = classify_membership("Bebidas", "Bebidas", "inferred")
    assert res == UNKNOWN
    assert reason == "insufficient_evidence"
    
def test_heuristic_category_match_is_unknown():
    res, reason = classify_membership("Sushi", "Sushi", "heuristic")
    assert res == UNKNOWN

def test_known_collection_exact_match():
    res, reason = classify_membership(" Ofertas  ", "Bebidas", "provider")
    assert res == COLLECTION
    assert reason == "known_rappi_collection"
    
    res, reason = classify_membership("Last Chance Deals", "", "provider")
    assert res == COLLECTION

def test_unknown_membership():
    res, reason = classify_membership("Random Corridor", "Bebidas", "provider")
    assert res == UNKNOWN

def test_homonymous_corridor_without_provider_match():
    # Morita Roll corridor containing Morita Roll product.
    # The product category might be Sushi, not Morita Roll.
    res, reason = classify_membership("Morita Roll", "Sushi", "provider")
    assert res == UNKNOWN

def test_conflicting_evidence():
    # Very rare: Rappi explicitly tags the category as "Ofertas"
    # But "Ofertas" is also in the Known Collections dictionary.
    res, reason = classify_membership("Ofertas", "Ofertas", "provider")
    assert res == UNKNOWN
    assert reason == "conflicting_evidence"
