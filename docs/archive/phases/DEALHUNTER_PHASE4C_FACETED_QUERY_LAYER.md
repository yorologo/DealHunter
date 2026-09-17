# DealHunter Phase 4C - Faceted Query Layer

## Overview
Phase 4C successfully replaces the legacy string-concatenation query engine with a robust, parameterized, faceted query engine (`src/dealhunter/query_layer.py`). It adheres to the fundamental boolean rule: **OR within a dimension, AND across dimensions**.

## Core Semantics Implemented
- **Store Facets (M:N)**: A product matches if its `store_id` has a facet present in `store_facets`. Implemented using `EXISTS (SELECT 1 FROM store_facets ...)` to prevent Cartesian explosion duplicates.
- **Collections (M:N)**: A product matches if it exists in `product_memberships`. Implemented using `EXISTS (SELECT 1 FROM product_memberships ...)`.
- **Category (1:N & M:N Fallback)**: The most critical logic. We query the trusted `product_memberships` table for category matches. If a product does NOT exist in `product_memberships` (due to partial crawler migration), it falls back to matching against `products.category` (legacy).
  - SQL Logic: `(EXISTS(trusted category) OR (NOT EXISTS(any trusted for this product) AND legacy category match))`
- **Commercial Channels (Public vs PRO)**: 
  - `PUBLIC`: Filter by `discount_effective >= min_discount`.
  - `PRO`: Requires `has_pro_offer = 1` AND `pro_discount_effective >= min_discount`.
  - Nulls (`has_pro_offer IS NULL`) represent unknown states and evaluate to false when explicitly requesting `PRO` filters, strictly adhering to the "Conservative Conclusions" rule.

## Architecture
The `build_faceted_query` dynamically constructs a parametrized SQL string and arguments array. It wraps an inner `base_query` which deduplicates history by leveraging `ROW_NUMBER() OVER (PARTITION BY store_id, product_id ORDER BY timestamp DESC, ROWID DESC) as rn = 1`.

## Performance Benchmarks
Tested against an 80,000 observation production SQLite database (`rappi-deals.db`) on Termux/Android:
- **Basic Query (No filters)**: Median 536ms | P95 570ms
- **Sort by Discount**: Median 585ms | P95 595ms
- **Vertical Filter (Restaurantes)**: Median 556ms | P95 565ms
- **Facet Counts**: Median 870ms

Performance is entirely bounded by the `ROW_NUMBER()` historical deduplication. Given the Termux mobile environment and lack of materialized views, ~500ms is highly interactive and acceptable.

## Web Integration
The legacy `/turbo`, `/market`, and `/deals` endpoints in `dealhunter/web/queries.py` (`get_catalog`) were updated to correctly translate frontend `request.args` into the new faceted `filters` dictionary schema. Test mock databases were upgraded and verified against the V12 DB schema. All 387 automated tests pass.
