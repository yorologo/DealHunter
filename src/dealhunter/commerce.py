"""Structured commerce classification for provider store listings.

This module intentionally classifies only provider-supplied structured type values.
Display names, brands, product names, and free-text tags are never authority for
commerce type or catalog domain.
"""

COMMERCE_UNKNOWN = "UNKNOWN"
DOMAIN_UNKNOWN = "UNKNOWN"
DOMAIN_RETAIL = "RETAIL"
DOMAIN_MENU = "MENU"

# Exact normalized provider type values that have an established meaning.
# Unknown values remain UNKNOWN rather than being guessed from display text.
_STRUCTURED_TYPES = {
    "restaurant": ("RESTAURANT", DOMAIN_MENU),
    "restaurants": ("RESTAURANT", DOMAIN_MENU),
    "grocery": ("SUPERMARKET", DOMAIN_RETAIL),
    "market": ("SUPERMARKET", DOMAIN_RETAIL),
    "super": ("SUPERMARKET", DOMAIN_RETAIL),
    "supermarket": ("SUPERMARKET", DOMAIN_RETAIL),
    "chiper_home": ("SUPERMARKET", DOMAIN_RETAIL),
    "chiper_extended": ("SUPERMARKET", DOMAIN_RETAIL),
    "chiper_express": ("SUPERMARKET", DOMAIN_RETAIL),
    "farmatodo": ("PHARMACY", DOMAIN_RETAIL),
    "pharmacy": ("PHARMACY", DOMAIN_RETAIL),
    "farmacia": ("PHARMACY", DOMAIN_RETAIL),
    "express_parent": ("SPECIALTY_RETAIL", DOMAIN_RETAIL),
    "pets_cpgs": ("SPECIALTY_RETAIL", DOMAIN_RETAIL),
}


def classify_store(raw_type, *, display_name=None):
    """Return ``(commerce_type, catalog_domain)`` from structured type evidence.

    ``display_name`` is accepted only to make the non-use of names explicit at
    call sites and tests. It is deliberately ignored.
    """
    del display_name
    if raw_type is None:
        return COMMERCE_UNKNOWN, DOMAIN_UNKNOWN
    key = str(raw_type).strip().lower()
    return _STRUCTURED_TYPES.get(key, (COMMERCE_UNKNOWN, DOMAIN_UNKNOWN))


def raw_types_for_commerce(commerce_types):
    wanted = set(commerce_types or [])
    return tuple(sorted(raw for raw, (commerce, _domain) in _STRUCTURED_TYPES.items() if commerce in wanted))


def raw_types_for_domain(catalog_domains):
    wanted = set(catalog_domains or [])
    return tuple(sorted(raw for raw, (_commerce, domain) in _STRUCTURED_TYPES.items() if domain in wanted))
