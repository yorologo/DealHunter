import pytest
from dealhunter.identity.normalization import parse_package, extract_signature, is_hard_reject

def test_parse_package():
    c, pu, t, u = parse_package("Coca Cola 8 x 42.5 g", None, None)
    assert c == 8
    assert pu == 42.5
    assert t == 340.0
    assert u == 'g'

    c, pu, t, u = parse_package("Leche 12 x 1 L", None, None)
    assert c == 12
    assert pu == 1000.0
    assert t == 12000.0
    assert u == 'ml'

def test_exact_unit_normalization():
    sig1 = extract_signature("Lala", "Leche 1 L", 1, "L")
    sig2 = extract_signature("Lala", "Leche 1000 ml", 1000, "ml")
    rejected, _ = is_hard_reject(sig1, sig2)
    assert rejected is False

    sig3 = extract_signature("Marca", "Harina 1 kg", 1, "kg")
    sig4 = extract_signature("Marca", "Harina 1000 g", 1000, "g")
    rejected, _ = is_hard_reject(sig3, sig4)
    assert rejected is False

    sig5 = extract_signature("Marca", "Harina 950 g", 950, "g")
    rejected, _ = is_hard_reject(sig3, sig5)
    assert rejected is True

def test_approximate_quantity():
    sig = extract_signature("Frutas", "Plátano aprox 1 kg", 1, "kg")
    assert sig["approximate_quantity"] is True
