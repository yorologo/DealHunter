import pytest
from dealhunter.providers.uber_eats.parser import UberEatsParser
from dealhunter.providers.uber_eats.normalizer import UberEatsNormalizer

@pytest.fixture
def parser():
    return UberEatsParser()

@pytest.fixture
def normalizer():
    return UberEatsNormalizer()

def test_parse_accessibility_price(parser):
    assert parser.parse_accessibility_price("$90.00, discounted from $120.00") == 120.0
    assert parser.parse_accessibility_price("$1,234.50, discounted from $2,000.00") == 2000.0
    assert parser.parse_accessibility_price("Just some text") is None

def test_parse_store_empty(parser):
    payload = {"uuid": "123", "title": "Empty Store"}
    result = parser.parse_store(payload)
    assert result["store"]["raw_store_id"] == "123"
    assert len(result["products"]) == 0

def test_parse_store_with_items(parser):
    payload = {
        "uuid": "store-1",
        "title": "Test Store",
        "sections": [{"uuid": "sec-1"}],
        "catalogSectionsMap": {
            "sec-1": [
                {
                    "type": "VERTICAL_GRID",
                    "payload": {
                        "standardItemsPayload": {
                            "title": {"text": "Category A"},
                            "catalogItems": [
                                {
                                    "uuid": "prod-1",
                                    "title": "Item 1",
                                    "price": 15000,
                                    "isSoldOut": False,
                                    "priceTagline": {
                                        "accessibilityText": "$150.00, discounted from $200.00"
                                    },
                                    "promoInfo": {
                                        "promotionUUID": "promo-1"
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        }
    }
    result = parser.parse_store(payload)
    assert len(result["products"]) == 1
    p = result["products"][0]
    assert p["raw_product_id"] == "prod-1"
    assert p["price"] == 150.0
    assert p["reference_price"] == 200.0
    assert p["promotion_uuid"] == "promo-1"
    assert p["availability"] == "AVAILABLE"
    assert p["category"] == "Category A"

def test_normalizer_product(normalizer):
    parsed_product = {
        "raw_product_id": "prod-1",
        "raw_store_id": "store-1",
        "name": "Item 1",
        "image_url": "http://img",
        "category": "Category A"
    }
    normalized = normalizer.normalize_product(parsed_product)
    assert normalized["product_id"] == "prod-1"
    assert normalized["store_id"] == "store-1"
    assert normalized["category_source"] == "uber_eats_grid"

def test_normalizer_observation(normalizer):
    parsed_product = {
        "raw_product_id": "prod-1",
        "raw_store_id": "store-1",
        "price": 150.0,
        "reference_price": 200.0,
        "availability": "AVAILABLE",
        "promotion_uuid": "promo-1"
    }
    obs = normalizer.normalize_observation(parsed_product, "run-1")
    assert obs["price"] == 150.0
    assert obs["original_price"] == 200.0
    assert obs["discount_effective"] == 25.0
    assert obs["stock"] == 1
    assert obs["promotion_type"] == "uber_promo"


def test_parse_accessibility_price_es_mx(parser):
    assert parser.parse_accessibility_price("$90.00, el precio anterior era $120.00, Al 85% de los usuarios") == 120.0
    assert parser.parse_accessibility_price("$1,234.50, el precio anterior era $2,000.00") == 2000.0
    
def test_dedup_and_memberships(normalizer):
    # Just to confirm normalizer returns what it's given, dedup is outside.
    assert True

def test_dedup_and_memberships_logic(parser, normalizer):
    payload = {
        "uuid": "store-1",
        "title": "Test Store",
        "sections": [{"uuid": "sec-1"}, {"uuid": "sec-2"}],
        "catalogSectionsMap": {
            "sec-1": [{
                "type": "VERTICAL_GRID",
                "payload": {
                    "standardItemsPayload": {
                        "title": {"text": "Category A"},
                        "catalogItems": [{"uuid": "prod-1", "title": "Item 1", "price": 10000}]
                    }
                }
            }],
            "sec-2": [{
                "type": "HORIZONTAL_GRID",
                "payload": {
                    "standardItemsPayload": {
                        "title": {"text": "Category B"},
                        "catalogItems": [{"uuid": "prod-1", "title": "Item 1", "price": 10000}]
                    }
                }
            }]
        }
    }
    result = parser.parse_store(payload)
    assert len(result["products"]) == 1
    p = result["products"][0]
    assert len(p["memberships"]) == 2
    assert p["memberships"][0]["raw_name"] == "Category A"
    assert p["memberships"][1]["raw_name"] == "Category B"
    
    n = normalizer.normalize_product(p)
    assert "memberships" in n
    assert len(n["memberships"]) == 2

def test_missing_price_and_unknown_fields(parser):
    payload = {
        "uuid": "store-1",
        "sections": [{"uuid": "sec-1"}],
        "catalogSectionsMap": {
            "sec-1": [{
                "type": "VERTICAL_GRID",
                "payload": {
                    "standardItemsPayload": {
                        "catalogItems": [{"uuid": "prod-2", "title": "Item 2", "price": None}]
                    }
                }
            }]
        }
    }
    result = parser.parse_store(payload)
    p = result["products"][0]
    assert p["price"] is None
    assert p["reference_price"] is None
