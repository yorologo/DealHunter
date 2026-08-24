"""
Conservative Semantic Classifier for DealHunter Phase 3B.
Operates exclusively in-memory on RAW memberships.
"""
import re
from typing import Tuple

CATEGORY = "CATEGORY"
COLLECTION = "COLLECTION"
UNKNOWN = "UNKNOWN"

KNOWN_COLLECTIONS = {
    "promos", "ofertas", "descuentos", "populares",
    "destacados", "last chance", "last chance deals", "ofertas pro"
}

def normalize_name(name: str) -> str:
    """Minimal normalization for safe string comparison: trim, casefold, collapse spaces."""
    if not name:
        return ""
    return re.sub(r'\s+', ' ', name).strip().casefold()

def classify_membership(membership_raw_name: str, product_category: str, product_category_source: str, raw_type: str = "") -> Tuple[str, str]:
    """
    Classifies a single membership conservatively based on provided evidence.
    Returns: (SEMANTIC_TYPE, reason)
    """
    norm_name = normalize_name(membership_raw_name)
    if not norm_name:
        return UNKNOWN, "empty_name"


    if raw_type == "generic":
        return CATEGORY, "web_exact_category_id"
    if raw_type in ["seasonal", "collection_view"]:
        return COLLECTION, "web_exact_collection_id"

    # Evidence for CATEGORY: product official category matches the membership name

    is_cat = False
    if product_category_source in ("provider", "rappi") and product_category:
        norm_product_cat = normalize_name(product_category)
        if norm_product_cat == norm_name:
            is_cat = True

    # Evidence for COLLECTION: exact match with known dictionary
    is_col = norm_name in KNOWN_COLLECTIONS

    if is_cat and is_col:
        return UNKNOWN, "conflicting_evidence"
    
    if is_cat:
        return CATEGORY, "matches_provider_category"
        
    if is_col:
        return COLLECTION, "known_rappi_collection"
        
    return UNKNOWN, "insufficient_evidence"

