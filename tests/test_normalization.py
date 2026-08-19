import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dealhunter.normalization import parse_product_name, calculate_unit_price, generate_fingerprint

def test_normalization_basic():
    res = parse_product_name("Coca Cola 2L", "Coca-Cola")
    assert res["brand"] == "coca-cola"
    assert res["normalized_name"] == "coca cola"
    assert res["quantity"] == 2
    assert res["unit"] == "L"
    assert res["normalized_quantity"] == 2
    assert res["normalized_unit"] == "L"

def test_normalization_ml_to_L():
    res = parse_product_name("Coca-Cola 2000 ml", "Coca-Cola")
    assert res["quantity"] == 2000
    assert res["unit"] == "ml"
    assert res["normalized_quantity"] == 2.0
    assert res["normalized_unit"] == "L"
    
def test_normalization_g_to_kg():
    res = parse_product_name("Arroz 900 g", "")
    assert res["quantity"] == 900
    assert res["unit"] == "g"
    assert res["normalized_quantity"] == 0.9
    assert res["normalized_unit"] == "kg"
    
    res = parse_product_name("Croquetas 3 kg", "")
    assert res["quantity"] == 3
    assert res["unit"] == "kg"
    assert res["normalized_quantity"] == 3
    assert res["normalized_unit"] == "kg"

def test_normalization_pieces():
    res = parse_product_name("Huevos 12 piezas", "")
    assert res["quantity"] == 12
    assert res["unit"] == "pieza"
    
    res = parse_product_name("Paracetamol 20 tabletas", "")
    assert res["quantity"] == 20
    assert res["unit"] == "tableta"

def test_normalization_packs():
    res = parse_product_name("Refresco 6 pack 355 ml", "")
    assert res["quantity"] == 2130.0  # 6 * 355
    assert res["unit"] == "ml"
    assert res["normalized_quantity"] == 2.13
    assert res["normalized_unit"] == "L"

def test_normalization_missing():
    res = parse_product_name("Leche entera", "")
    assert res["quantity"] is None
    assert res["unit"] is None
    assert res["normalized_quantity"] is None
    assert res["normalized_unit"] is None

def test_unit_price():
    assert calculate_unit_price(180, 2) == 90.0
    assert calculate_unit_price(120, 1) == 120.0
    assert calculate_unit_price(60, 12) == 5.0
    assert calculate_unit_price(100, None) is None
    assert calculate_unit_price(100, 0) is None

def test_fingerprint():
    # brand, name, qty, unit
    fp = generate_fingerprint("coca-cola", "original", 2, "L")
    assert fp == "coca-cola|original|2|l"
    
    fp2 = generate_fingerprint("", "leche entera", None, None)
    assert fp2 == "leche-entera"

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nNormalization tests: {passed} total, {passed} passed, 0 failed.")
