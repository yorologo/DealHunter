import pytest
from dealhunter.semantic import classify_membership, CATEGORY, COLLECTION, UNKNOWN

def test_semantic_category_rule():
    # raw_type='generic' should be CATEGORY
    stype, reason = classify_membership("Despensa", "", "", raw_type="generic")
    assert stype == CATEGORY
    assert reason == "web_exact_category_id"

def test_semantic_collection_rule():
    # raw_type='seasonal' should be COLLECTION
    stype, reason = classify_membership("Regreso a Clases", "", "", raw_type="seasonal")
    assert stype == COLLECTION
    assert reason == "web_exact_collection_id"
    
    # raw_type='collection_view' should be COLLECTION
    stype, reason = classify_membership("Ofertas", "", "", raw_type="collection_view")
    assert stype == COLLECTION
    assert reason == "web_exact_collection_id"

def test_semantic_unknown_rule():
    # raw_type='unknown' should still fall back to previous rules
    stype, reason = classify_membership("Random", "", "", raw_type="unknown")
    assert stype == UNKNOWN
