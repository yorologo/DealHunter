# Rappi Taxonomy Crosswalk
This document explains the recovery crosswalk mapping applied during Phase 4F to resolve legacy `UNKNOWN` semantic memberships.

## The Problem
Early V13 crawls used the Android Primary payload, which omitted explicit `aisle_type` parameters, causing 8,732 items to fallback to `UNKNOWN`.

## The Crosswalk Solution
By matching the Android `raw_id` against the Web SSR `__NEXT_DATA__` payload for 5 strategic stores (Costco, City Market, Sally Beauty, Turbo, Sushi Central), we mapped exact container identifiers (like `raw_id=256` "Bebidas") to their explicitly typed `aisle_type` (e.g. `generic` = CATEGORY, `seasonal` = COLLECTION).

## Rule Invariance
A backfill audit (Phase 4F.1) confirmed:
- **Global Invariance**: 29 `raw_id`s spanned multiple vertical contexts identically without collisions.
- **Context Invariance**: 23 `raw_id`s remained firmly scoped to their parent types (e.g., Turbo `express_parent`) with zero collisions.

## Future Pipeline
The static crosswalk is **not** a persistent engine dependency. The crawler (`catalog_sync.py`) natively extracts `aisle_type` and `view_config` going forward, enabling autonomous classification of all future memberships seamlessly.
