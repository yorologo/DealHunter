import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.normalization import compute_match, canonicalize_text

def _mock_prod(brand, name, qty, unit):
    return {
        "brand": brand,
        "normalized_name": canonicalize_text(name),
        "normalized_quantity": qty,
        "normalized_unit": unit,
        "fingerprint": f"{brand}|{canonicalize_text(name)}|{qty}|{unit}" if brand else "unknown"
    }

def test_canonicalize_text():
    assert canonicalize_text("Coca-Cola") == "coca cola"
    assert canonicalize_text("coca cola") == "coca cola"
    assert canonicalize_text("Coca Cola  Zero!") == "coca cola zero"

def test_exact_match():
    p1 = _mock_prod("coca cola", "original", 2, "L")
    p2 = _mock_prod("coca cola", "original", 2, "L")
    m_type, _ = compute_match(p1, p2)
    assert m_type == "EXACT_MATCH"

def test_high_confidence_match():
    p1 = _mock_prod("coca cola", "original", 2, "L")
    p2 = _mock_prod("coca cola", "refresco original", 2, "L")
    m_type, conf = compute_match(p1, p2)
    assert m_type == "HIGH_CONFIDENCE_MATCH"
    assert conf > 0.0
    
    p3 = _mock_prod("leche marca x", "entera", 1, "L")
    p4 = _mock_prod("leche marca x", "entera fortificada", 1, "L")
    m_type, conf = compute_match(p3, p4)
    assert m_type == "HIGH_CONFIDENCE_MATCH"

def test_no_match():
    # different variants
    p1 = _mock_prod("coca cola", "original", 2, "L")
    p2 = _mock_prod("coca cola", "zero", 2, "L")
    assert compute_match(p1, p2)[0] == "NO_MATCH"
    
    # different size
    p3 = _mock_prod("coca cola", "original", 0.6, "L")
    p4 = _mock_prod("coca cola", "original", 2, "L")
    assert compute_match(p3, p4)[0] == "NO_MATCH"
    
    # different categories / incompatible
    p5 = _mock_prod("marca x", "leche entera", 1, "L")
    p6 = _mock_prod("marca x", "leche deslactosada", 1, "L")
    assert compute_match(p5, p6)[0] == "NO_MATCH"
    
    p7 = _mock_prod("marca y", "shampoo", 0.4, "L")
    p8 = _mock_prod("marca y", "acondicionador", 0.4, "L")
    assert compute_match(p7, p8)[0] == "NO_MATCH"

def test_fuzzy_match():
    # typo simple
    p1 = _mock_prod("cacahuates", "cacahuate tostado", 500, "g")
    p2 = _mock_prod("cacahuates", "cacahuete tostado", 500, "g")
    m_type, conf = compute_match(p1, p2)
    assert m_type == "FUZZY_MATCH"
    assert conf < 0.70
    
    # words transposed should work with sorted canonicalization
    p3 = _mock_prod("sabritas", "papas fritas originales", 100, "g")
    p4 = _mock_prod("sabritas", "originales papas fritas", 100, "g")
    m_type, _ = compute_match(p3, p4)
    # This might actually hit HIGH_CONFIDENCE because it's a perfect word match
    assert m_type in ("HIGH_CONFIDENCE_MATCH", "FUZZY_MATCH")

    # missing accent vs non missing is solved by canonicalize
    p5 = _mock_prod("nestle", "café", 200, "g")
    p6 = _mock_prod("nestle", "cafe", 200, "g")
    assert compute_match(p5, p6)[0] == "EXACT_MATCH"

def test_fuzzy_no_match_on_hard_rules():
    # hard conflicts cannot be saved by fuzzy
    p1 = _mock_prod("coca cola", "original", 2, "L")
    p2 = _mock_prod("coca cola", "zero", 2, "L")
    # words: "original" vs "zero". ratio is low anyway, but hard constraint should block it.
    assert compute_match(p1, p2)[0] == "NO_MATCH"
    
    p3 = _mock_prod("lala", "leche entera", 1, "L")
    p4 = _mock_prod("lala", "leche enterra", 1, "L")
    assert compute_match(p3, p4)[0] == "FUZZY_MATCH"
    
    # different quantities block fuzzy
    p5 = _mock_prod("cacahuates", "cacahuete tostado", 500, "g")
    p6 = _mock_prod("cacahuates", "cacahuate tostado", 400, "g")
    assert compute_match(p5, p6)[0] == "NO_MATCH"

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nMatching tests: {passed} total, {passed} passed, 0 failed.")
