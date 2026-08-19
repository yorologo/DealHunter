import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.normalization import (
    canonicalize_text,
    compute_match,
    generate_fingerprint,
    parse_product_name,
)

def _mock_prod(brand, name, qty, unit, pack_count=1):
    return {
        "brand": brand,
        "normalized_name": canonicalize_text(name),
        "normalized_quantity": qty,
        "normalized_unit": unit,
        "pack_count": pack_count,
        "fingerprint": generate_fingerprint(
            brand, canonicalize_text(name), qty, unit, pack_count
        ),
    }

def _parsed_prod(raw_name, brand):
    normalized = parse_product_name(raw_name, brand)
    normalized["name"] = raw_name
    normalized["fingerprint"] = generate_fingerprint(
        normalized["brand"], normalized["normalized_name"],
        normalized["normalized_quantity"], normalized["normalized_unit"],
        normalized["pack_count"]
    )
    return normalized

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

def test_regression_deslactosada_vs_capuccino():
    p1 = _mock_prod(
        "Santa Clara", "Leche Deslactosada Semidescremada", 1, "L"
    )
    p2 = _mock_prod(
        "Santa Clara", "Leche UHT Semidescremada Capuccino", 1, "L"
    )
    assert compute_match(p1, p2)[0] == "NO_MATCH"

def test_semantic_variant_categories_are_hard_rules():
    incompatible_names = (
        ("Refresco Original", "Refresco Zero"),
        ("Refresco Original", "Refresco Light"),
        ("Refresco Original", "Refresco Diet"),
        ("Bebida Regular", "Bebida Sin Azucar"),
        ("Leche Sabor Fresa", "Leche Sabor Chocolate"),
        ("Bebida Vainilla", "Bebida"),
        ("Shampoo Reparador", "Acondicionador Reparador"),
        ("Alimento Adulto", "Alimento Cachorro"),
        ("Refresco Original", "Refresco"),
    )
    for name1, name2 in incompatible_names:
        p1 = _mock_prod("Marca", name1, 1, "L")
        p2 = _mock_prod("Marca", name2, 1, "L")
        assert compute_match(p1, p2)[0] == "NO_MATCH"

def test_regression_pack_of_two_vs_individual():
    pack = _parsed_prod("Leche Deslactosada 2 x 1 L", "Santa Clara")
    individual = _parsed_prod("Leche Deslactosada 1 L", "Santa Clara")
    assert compute_match(pack, individual)[0] == "NO_MATCH"

def test_regression_pack_of_six_vs_individual():
    pack = _parsed_prod("Refresco Original 6 x 355 ml", "Coca Cola")
    individual = _parsed_prod("Refresco Original 355 ml", "Coca Cola")
    assert compute_match(pack, individual)[0] == "NO_MATCH"

def test_regression_pan_bollo_vs_bolillo_pan():
    p1 = _mock_prod("Panaderia", "Pan Bollo", 4, "pieza")
    p2 = _mock_prod("Panaderia", "Bolillo Pan", 4, "pieza")
    assert compute_match(p1, p2)[0] == "NO_MATCH"

def test_equivalent_multipacks_match():
    two_x = _parsed_prod("Leche Deslactosada 2 x 1 L", "Santa Clara")
    pack_two = _parsed_prod(
        "Leche Deslactosada Pack 2 botellas 1L", "Santa Clara"
    )
    assert compute_match(two_x, pack_two)[0] == "EXACT_MATCH"

    six_x = _parsed_prod("Refresco Original 6 x 355 ml", "Coca Cola")
    pack_six = _parsed_prod(
        "Refresco Original Pack 6 latas 355 ml", "Coca Cola"
    )
    assert compute_match(six_x, pack_six)[0] == "EXACT_MATCH"

def test_required_typo_matches():
    coca_typo = _parsed_prod("Coca Colla Original 2 L", "Coca Cola")
    coca = _parsed_prod("Coca Cola Original 2 L", "Coca Cola")
    assert compute_match(coca_typo, coca)[0] in (
        "HIGH_CONFIDENCE_MATCH", "FUZZY_MATCH"
    )

    cacahuete = _parsed_prod("Cacahuete 500 g", "Marca X")
    cacahuate = _parsed_prod("Cacahuate 500 g", "Marca X")
    assert compute_match(cacahuete, cacahuate)[0] == "FUZZY_MATCH"

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
    assert compute_match(p3, p4)[0] == "NO_MATCH"
    
    # different quantities block fuzzy
    p5 = _mock_prod("cacahuates", "cacahuete tostado", 500, "g")
    p6 = _mock_prod("cacahuates", "cacahuate tostado", 400, "g")
    assert compute_match(p5, p6)[0] == "NO_MATCH"

def test_unknown_size_never_uses_high_or_fuzzy():
    p1 = _mock_prod("marca", "cacahuete tostado", None, None, None)
    p2 = _mock_prod("marca", "cacahuate tostado", None, None, None)
    assert compute_match(p1, p2)[0] == "NO_MATCH"

    exact1 = _mock_prod("marca", "producto identico", None, None, None)
    exact2 = _mock_prod("marca", "producto identico", None, None, None)
    assert compute_match(exact1, exact2)[0] == "EXACT_MATCH"

def test_high_requires_brand_and_non_generic_semantics():
    no_brand1 = _mock_prod("", "cacahuete tostado", 0.5, "kg")
    no_brand2 = _mock_prod("", "cacahuate tostado", 0.5, "kg")
    assert compute_match(no_brand1, no_brand2)[0] == "NO_MATCH"

    generic1 = _mock_prod("marca", "leche bebida", 1, "L")
    generic2 = _mock_prod("marca", "leche refresco producto", 1, "L")
    assert compute_match(generic1, generic2)[0] == "NO_MATCH"

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nMatching tests: {passed} total, {passed} passed, 0 failed.")
