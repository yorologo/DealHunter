# Rappi Open Questions & Technical Debt

This document tracks unresolved contracts, unexplored surfaces, and pending migrations specific to the Rappi integration.

### BLOCKING
*(None currently block Phase 4 or 5 completion, but may block specific vertical reliability).*
- **Pro Population After First V12 Crawl**: The V12 schema is live, but the crawler must successfully complete a production run to populate `pro_price` and `has_pro_offer` before the UI can effectively demonstrate it to users.
- **Faceted Coverage After Production Population**: We must measure how much of the existing legacy `products.category` catalogue gets successfully mapped to `product_memberships` during the first faceted crawl.

### NON_BLOCKING
- **Restaurants Android vs Web SSR**: Currently, Restaurants are primarily handled via Web fallbacks. The Android native surface for restaurants remains partially explored.
- **Liquor Discovery Completeness**: A5 did not natively discover certain liquor legacy stores. We rely on the Unified Search / Web fallback. Is there a dedicated Android liquor surface?

### DEFERRED
- **Android Product Taxonomy Deeper Surface**: The deeply nested categorical navigation beyond the primary D1/B1 feeds.
- **Offers/Home Router ROI**: Evaluating if parsing the highly personalized "Home Router" feed yields better deals than systematic category crawling.
- **B1 Unresolved Contract**: Some quirks in the B1 Turbo response pagination remain partially understood.
- **PDP (Product Detail Page)**: Deferred until there is a strict feature requirement (e.g., extracting hyper-specific descriptions or terms) since catalog views provide 99% of pricing intel.

## Phase 4F Updates
- **Android product taxonomy deeper surface**: [RESOLVED] We bypassed the need for deeper Android-specific taxonomy endpoints by crosswalking the exact `raw_id`s with the Web SSR `__NEXT_DATA__` during normal catalog sync, extracting `aisle_type` directly at zero extra cost.
- **Web taxonomy dependency**: [RESOLVED] Integrated exclusively as a zero-cost secondary enrichment on the existing catalog requests. Web is not a blocking dependency for discovery.
- **Restaurant taxonomy**: [DEFERRED] Remains isolated. The generic `corridor` concepts from CPG do not apply safely to menus without risking pollution.
