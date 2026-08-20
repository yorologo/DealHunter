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
    assert res["pack_count"] == 1

def test_normalization_liter_aliases():
    for raw_name, expected_quantity in (
        ("Leche 1 lt", 1),
        ("Leche 2 lt", 2),
        ("Leche 1 l", 1),
        ("Leche 2 litros", 2),
        ("Leche 1.5 litro", 1.5),
    ):
        res = parse_product_name(raw_name, "Lala")
        assert res["normalized_name"] == "leche"
        assert res["quantity"] == expected_quantity
        assert res["unit"] == "L"
        assert res["normalized_quantity"] == expected_quantity
        assert res["normalized_unit"] == "L"

def test_normalization_full_words():
    tests = [
        ("Agua 625 Mililitros", 625, "ml", 0.625, "L"),
        ("Queso 500 gramos", 500, "g", 0.5, "kg"),
        ("Manzana 2 kilogramos", 2, "kg", 2, "kg"),
        ("Pastillas 20 miligramos", 20, "mg", 0.00002, "kg")
    ]
    for raw_name, q, u, nq, nu in tests:
        res = parse_product_name(raw_name, "Test")
        assert res["quantity"] == q
        assert res['unit'] == u
        assert res['normalized_quantity'] == nq
        assert res['normalized_unit'] == nu
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
    assert res["pack_count"] == 6

def test_normalization_multiplier_packs():
    cases = (
        ("Leche 2 x 1 L", 2, "L", 2.0, "L", 2),
        ("Leche 2x1 L", 2, "L", 2.0, "L", 2),
        ("Refresco 2 x 355 ml", 710, "ml", 0.71, "L", 2),
        ("Refresco 6 x 355 ml", 2130, "ml", 2.13, "L", 6),
        ("Leche 2 x botella 1 L", 2, "L", 2.0, "L", 2),
        ("Leche Pack 2 botellas 1L", 2, "L", 2.0, "L", 2),
        ("Refresco Pack 6 latas de 355 ml", 2130, "ml", 2.13, "L", 6),
    )
    for raw_name, quantity, unit, normalized_quantity, normalized_unit, pack_count in cases:
        res = parse_product_name(raw_name, "Marca")
        assert res["normalized_name"] in ("leche", "refresco")
        assert res["quantity"] == quantity
        assert res["unit"] == unit
        assert res["normalized_quantity"] == normalized_quantity
        assert res["normalized_unit"] == normalized_unit
        assert res["pack_count"] == pack_count

def test_normalization_multiplier_without_size_preserves_pack():
    res = parse_product_name("2 x Santa Clara Leche Deslactosada", "Santa Clara")
    assert res["normalized_name"] == "santa clara leche deslactosada"
    assert res["normalized_quantity"] is None
    assert res["normalized_unit"] is None
    assert res["pack_count"] == 2

def test_normalization_missing():
    res = parse_product_name("Leche entera", "")
    assert res["quantity"] is None
    assert res["unit"] is None
    assert res["normalized_quantity"] is None
    assert res["normalized_unit"] is None
    assert res["pack_count"] is None

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

    pack_fp = generate_fingerprint("marca", "refresco", 2.13, "L", 6)
    assert pack_fp == "marca|refresco|2.13|l|pack-6"

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS  {t.__name__}")
    print(f"\nNormalization tests: {passed} total, {passed} passed, 0 failed.")

def test_unit_price_formatting_special_cases():
    from dealhunter.normalization import format_unit_price
    
    # 620 g at $62 -> $100/kg
    # The normalizer yields normalized_quantity=0.62, normalized_unit='kg'
    assert format_unit_price(62.0, 0.62, 'kg') == '$100/kg'
    
    # 1 kg at $20.80 -> $20.8/kg
    assert format_unit_price(20.80, 1.0, 'kg') == '$20.8/kg'
    
    # 6 x 355 ml = 2.13 L at $120 -> 120 / 2.13 = $56.33/L
    assert format_unit_price(120.0, 2.13, 'L') == '$56.338/L'

def test_parse_product_name_multipacks():
    from dealhunter.normalization import parse_product_name
    
    # 6 x 355 ml
    parsed = parse_product_name("Cerveza 6 x 355 ml")
    assert parsed["pack_count"] == 6
    assert parsed["quantity"] == 2130
    assert parsed["unit"] == "ml"
    assert parsed["normalized_quantity"] == 2.13
    assert parsed["normalized_unit"] == "L"
    
    # 12 pack
    parsed = parse_product_name("Agua 12 pack")
    assert parsed["pack_count"] == 12
    assert parsed["unit"] == "pack"
    assert parsed["normalized_quantity"] == 12
    assert parsed["normalized_unit"] == "pack"
