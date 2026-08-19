import difflib
import math
import re
import unicodedata


UNIT_MAP = {
    "g": "g",
    "gramo": "g",
    "gramos": "g",
    "kg": "kg",
    "kilogramo": "kg",
    "kilogramos": "kg",
    "mg": "mg",
    "miligramo": "mg",
    "miligramos": "mg",
    "ml": "ml",
    "mililitro": "ml",
    "mililitros": "ml",
    "l": "L",
    "lt": "L",
    "lts": "L",
    "litro": "L",
    "litros": "L",
    "pz": "pieza",
    "pza": "pieza",
    "pzas": "pieza",
    "pieza": "pieza",
    "piezas": "pieza",
    "tableta": "tableta",
    "tabletas": "tableta",
    "cápsula": "cápsula",
    "cápsulas": "cápsula",
    "capsula": "cápsula",
    "capsulas": "cápsula",
    "pack": "pack",
}

_UNIT_PATTERN = (
    r"kilogramos?|kg|miligramos?|mg|mililitros?|ml|gramos?|g|litros?|lts?|l|piezas?|pzas?|pz|"
    r"tabletas?|c[aá]psulas?"
)
_CONTAINER_PATTERN = r"botellas?|latas?|envases?|unidades?"
_NUMBER_PATTERN = r"\d+(?:[.,]\d+)?"

# Explicit multipacks. The full expression is removed from normalized_name so
# packaging words cannot manufacture semantic overlap in the matcher.
_PACK_PATTERNS = (
    re.compile(
        rf"\b(?P<count>\d+)\s*[x×]\s*"
        rf"(?:(?:{_CONTAINER_PATTERN})\s+)?"
        rf"(?P<per>{_NUMBER_PATTERN})\s*(?P<unit>{_UNIT_PATTERN})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bpack\s+(?:de\s+)?(?P<count>\d+)\s+"
        rf"(?:(?:{_CONTAINER_PATTERN})\s*(?:de\s+)?)?"
        rf"(?P<per>{_NUMBER_PATTERN})\s*(?P<unit>{_UNIT_PATTERN})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<count>\d+)\s*-?\s*(?:pack|paquete)\s*"
        rf"(?:(?:de\s+)?(?:{_CONTAINER_PATTERN})\s*(?:de\s+)?)?"
        rf"(?P<per>{_NUMBER_PATTERN})\s*(?P<unit>{_UNIT_PATTERN})\b",
        re.IGNORECASE,
    ),
)
_PACK_COUNT_ONLY_PATTERN = re.compile(
    r"\b(?P<count>\d+)\s*[x×]\s*", re.IGNORECASE
)
_PACK_ONLY_PATTERNS = (
    re.compile(r"\bpack\s+(?:de\s+)?(?P<count>\d+)\b", re.IGNORECASE),
    re.compile(
        r"\b(?P<count>\d+)\s*-?\s*(?:pack|paquete)\b", re.IGNORECASE
    ),
)
_QUANTITY_PATTERN = re.compile(
    rf"\b(?P<quantity>{_NUMBER_PATTERN})\s*(?P<unit>{_UNIT_PATTERN})\b",
    re.IGNORECASE,
)

# Each mapping is a small, testable semantic category. Values in the same
# category are incompatible unless both titles resolve to the same value set.
# Empty versus explicit is also a conflict: omission must not erase a variant.
_VARIANT_CATEGORIES = {
    "formula": {
        "original": ("original", "clasica", "clasico", "regular"),
        "zero": ("zero", "cero"),
        "light": ("light", "ligera", "ligero"),
        "diet": ("diet", "dieta"),
    },
    "sugar": {
        "sugar_free": ("sin azucar", "sin azucares", "sugar free"),
    },
    "milk_type": {
        "whole": ("entera", "entero"),
        "lactose_free": (
            "deslactosada",
            "deslactosado",
            "sin lactosa",
        ),
        "skim": ("descremada", "descremado"),
        "semi_skim": ("semidescremada", "semidescremado"),
    },
    "flavor": {
        "strawberry": ("fresa",),
        "chocolate": ("chocolate",),
        "vanilla": ("vainilla",),
        "cappuccino": ("capuccino", "cappuccino", "capuchino"),
    },
    "hair_care": {
        "shampoo": ("shampoo", "shampu"),
        "conditioner": ("acondicionador",),
    },
    "life_stage": {
        "adult": ("adulto", "adulta", "adultos", "adultas"),
        "puppy": ("cachorro", "cachorra", "cachorros", "cachorras"),
    },
}

_GENERIC_MATCH_WORDS = {
    "bebida",
    "bebidas",
    "botella",
    "botellas",
    "lata",
    "latas",
    "leche",
    "pack",
    "paquete",
    "producto",
    "productos",
    "refresco",
    "refrescos",
}
_MIN_SHARED_SEMANTIC_CHARS = 5
_MIN_FUZZY_ALNUM_CHARS = 9


def canonicalize_text(text):
    if not text:
        return ""
    text = "".join(
        c
        for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    )
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _as_number(value):
    return float(value.replace(",", "."))


def _normalize_quantity(quantity, unit):
    normalized_quantity = quantity
    normalized_unit = unit

    if unit == "g" and quantity is not None:
        normalized_quantity = quantity / 1000.0
        normalized_unit = "kg"
    elif unit == "ml" and quantity is not None:
        normalized_quantity = quantity / 1000.0
        normalized_unit = "L"
    elif unit == "mg" and quantity is not None:
        normalized_quantity = quantity / 1000000.0
        normalized_unit = "kg"

    return normalized_quantity, normalized_unit


def parse_product_name(name, raw_brand=None):
    if not name:
        return {
            "normalized_name": "",
            "brand": (raw_brand or "").lower().strip(),
            "quantity": None,
            "unit": None,
            "normalized_quantity": None,
            "normalized_unit": None,
            "pack_count": None,
        }

    name = str(name).strip()
    matched_quantity = None
    quantity = None
    unit = None
    pack_count = None

    for pattern in _PACK_PATTERNS:
        matched_quantity = pattern.search(name)
        if matched_quantity:
            pack_count = int(matched_quantity.group("count"))
            per_unit_quantity = _as_number(matched_quantity.group("per"))
            raw_unit = canonicalize_text(matched_quantity.group("unit"))
            quantity = pack_count * per_unit_quantity
            unit = UNIT_MAP.get(raw_unit, raw_unit)
            break

    if matched_quantity is None:
        matched_quantity = _PACK_COUNT_ONLY_PATTERN.search(name)
        if matched_quantity:
            pack_count = int(matched_quantity.group("count"))

    if matched_quantity is None:
        for pattern in _PACK_ONLY_PATTERNS:
            matched_quantity = pattern.search(name)
            if matched_quantity:
                pack_count = int(matched_quantity.group("count"))
                quantity = float(pack_count)
                unit = "pack"
                break

    if matched_quantity is None:
        matched_quantity = _QUANTITY_PATTERN.search(name)
        if matched_quantity:
            quantity = _as_number(matched_quantity.group("quantity"))
            raw_unit = canonicalize_text(matched_quantity.group("unit"))
            unit = UNIT_MAP.get(raw_unit, raw_unit)
            pack_count = 1

    normalized_name = name
    if matched_quantity:
        normalized_name = (
            name[: matched_quantity.start()] + " " + name[matched_quantity.end() :]
        )
    normalized_name = canonicalize_text(normalized_name)

    normalized_quantity, normalized_unit = _normalize_quantity(quantity, unit)

    return {
        "brand": (raw_brand or "").lower().strip(),
        "normalized_name": normalized_name,
        "quantity": quantity,
        "unit": unit,
        "normalized_quantity": normalized_quantity,
        "normalized_unit": normalized_unit,
        "pack_count": pack_count,
    }


def calculate_unit_price(price, normalized_quantity):
    if price is None or normalized_quantity is None or normalized_quantity <= 0:
        return None
    return round(price / normalized_quantity, 2)

def format_unit_price(price, normalized_quantity, normalized_unit):
    if price is None or normalized_quantity is None or normalized_quantity <= 0 or not normalized_unit:
        return ""
    
    nu = normalized_unit.lower()
    if nu == 'ml':
        val = price * (1000 / normalized_quantity)
        unit_str = 'L'
    elif nu == 'l':
        val = price / normalized_quantity
        unit_str = 'L'
    elif nu == 'g':
        val = price * (1000 / normalized_quantity)
        unit_str = 'kg'
    elif nu == 'kg':
        val = price / normalized_quantity
        unit_str = 'kg'
    else:
        val = price / normalized_quantity
        unit_str = normalized_unit
        
    return f"${val:g}/{unit_str}"



def generate_fingerprint(
    brand, normalized_name, normalized_quantity, normalized_unit, pack_count=None
):
    brand = canonicalize_text(brand)
    name = canonicalize_text(normalized_name)

    parts = []
    if brand:
        parts.append(brand.replace(" ", "-"))
    if name:
        parts.append(name.replace(" ", "-"))
    if normalized_quantity is not None and normalized_unit:
        parts.append(f"{normalized_quantity:g}")
        parts.append(str(normalized_unit).lower())
    if pack_count is not None and pack_count > 1:
        parts.append(f"pack-{int(pack_count)}")

    return "|".join(parts) if parts else "unknown"


def _variant_profile(name):
    padded_name = f" {canonicalize_text(name)} "
    profile = {}
    for category, values in _VARIANT_CATEGORIES.items():
        found = set()
        for value, aliases in values.items():
            if any(f" {canonicalize_text(alias)} " in padded_name for alias in aliases):
                found.add(value)
        profile[category] = found
    return profile


def _has_variant_conflict(name1, name2):
    profile1 = _variant_profile(name1)
    profile2 = _variant_profile(name2)
    return any(profile1[category] != profile2[category] for category in profile1)


def _resolved_match_fields(product):
    raw_name = product.get("name") or product.get("product_name")
    parsed = parse_product_name(raw_name, product.get("brand")) if raw_name else None

    name = product.get("normalized_name")
    if name is None and parsed:
        name = parsed["normalized_name"]

    quantity = product.get("normalized_quantity")
    if quantity is None and parsed:
        quantity = parsed["normalized_quantity"]

    unit = product.get("normalized_unit")
    if unit is None and parsed:
        unit = parsed["normalized_unit"]

    pack_count = product.get("pack_count")
    if pack_count is None and parsed:
        pack_count = parsed["pack_count"]

    try:
        pack_count = int(pack_count) if pack_count is not None else None
    except (TypeError, ValueError):
        pack_count = None

    return canonicalize_text(name), quantity, unit, pack_count


def _same_quantity(q1, q2):
    try:
        return math.isclose(float(q1), float(q2), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return False


def _without_brand_words(name, brand1, brand2):
    words = set(name.split())
    words -= set(brand1.split())
    words -= set(brand2.split())
    return words


def compute_match(p1, p2):
    """Return ``(match_type, confidence)`` for two normalized products.

    EXACT may safely cover identical fingerprints with unknown sizes. HIGH and
    FUZZY require explicit, equal brand, size, unit and pack metadata and run
    only after every hard semantic rule has passed.
    """
    brand1 = canonicalize_text(p1.get("brand", ""))
    brand2 = canonicalize_text(p2.get("brand", ""))
    name1, q1, u1, pack1 = _resolved_match_fields(p1)
    name2, q2, u2, pack2 = _resolved_match_fields(p2)

    known_size1 = q1 is not None and bool(u1)
    known_size2 = q2 is not None and bool(u2)

    # Hard rules are intentionally evaluated before fingerprints so stale v3
    # fingerprints cannot merge a multipack with an individual presentation.
    if known_size1 != known_size2:
        return "NO_MATCH", 0.0
    if known_size1 and (
        not _same_quantity(q1, q2)
        or canonicalize_text(u1) != canonicalize_text(u2)
    ):
        return "NO_MATCH", 0.0
    if known_size1 and (pack1 is None or pack2 is None):
        return "NO_MATCH", 0.0
    if pack1 != pack2 and (pack1 is not None or pack2 is not None):
        return "NO_MATCH", 0.0
    if brand1 and brand2 and brand1 != brand2:
        return "NO_MATCH", 0.0
    if _has_variant_conflict(name1, name2):
        return "NO_MATCH", 0.0

    fp1 = p1.get("fingerprint")
    fp2 = p2.get("fingerprint")
    if fp1 and fp2 and fp1 == fp2 and fp1 != "unknown":
        return "EXACT_MATCH", 1.00

    # Unknown size is deliberately ineligible for approximate matching.
    if not known_size1 or not known_size2:
        return "NO_MATCH", 0.0

    # HIGH/FUZZY require an explicit identical brand, not merely no conflict.
    if not brand1 or not brand2 or brand1 != brand2:
        return "NO_MATCH", 0.0

    words1 = _without_brand_words(name1, brand1, brand2)
    words2 = _without_brand_words(name2, brand1, brand2)
    semantic1 = words1 - _GENERIC_MATCH_WORDS
    semantic2 = words2 - _GENERIC_MATCH_WORDS
    shared = semantic1.intersection(semantic2)
    shared_chars = sum(len(word) for word in shared)

    if shared and shared_chars >= _MIN_SHARED_SEMANTIC_CHARS:
        if semantic1.issubset(semantic2) or semantic2.issubset(semantic1):
            return "HIGH_CONFIDENCE_MATCH", 0.80

        overlap = len(shared) / max(len(semantic1), len(semantic2))
        if overlap >= 0.6:
            return "HIGH_CONFIDENCE_MATCH", 0.70

    # FUZZY is a typo-only fallback over non-generic semantic content.
    fuzzy_name1 = " ".join(sorted(semantic1))
    fuzzy_name2 = " ".join(sorted(semantic2))
    chars1 = sum(char.isalnum() for char in fuzzy_name1)
    chars2 = sum(char.isalnum() for char in fuzzy_name2)
    if (
        fuzzy_name1
        and fuzzy_name2
        and chars1 >= _MIN_FUZZY_ALNUM_CHARS
        and chars2 >= _MIN_FUZZY_ALNUM_CHARS
    ):
        ratio = difflib.SequenceMatcher(None, fuzzy_name1, fuzzy_name2).ratio()
        if ratio >= 0.85:
            return "FUZZY_MATCH", 0.60

    return "NO_MATCH", 0.0
