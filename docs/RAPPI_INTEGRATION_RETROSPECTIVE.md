# Rappi Integration Retrospective

## Context
The goal of DealHunter was to transition from a legacy, heuristic-heavy web scraping approach to a deterministic, reliable, and scalable integration natively aligned with the Rappi Android App's structured architecture.

## Legacy Discovery (Phase 4A)
- **Problem**: The web crawler relied on fragile endpoints that constantly broke, returned unpredictable payload structures, and hallucinated taxonomies via regex.
- **Experiment**: Audited the Rappi Android APK utilizing tools like Blutter and network interception via PCAP.
- **Result**: Discovered that Rappi operates an interconnected graph of Backend-For-Frontend (BFF) surfaces.

## Surface Reconnaissance (Phase 4B)
- **Problem**: Many endpoints (like B1 Context Resolve and D1 Catalog Dump) were either encrypted, tightly coupled to specific headers, or returned payload models too generic (or too specific) to handle unified queries.
- **Decision**: Deferred B1 and D1 due to low ROI. Standardized on the `A5` endpoint (Context Stores) which proved to be a high-yield Oracle returning perfectly nested metadata for Market, Turbo, and Restaurants.

## A5 and Scope Reconciliation (Phase 4C & 4D)
- **Problem**: When a store's catalog exceeded normal bounds, the crawler would miss items. A5 provided parent contexts, but the Web Oracle (used as secondary enrichment) would sometimes leak root taxonomy.
- **Experiment**: Introduced recursive SSR parsing and isolated A5's domain payload.
- **Result**: Safely bypassed web-only hallucination. Turbo replacement scopes were handled cleanly.

## Taxonomy M:N & SSR Bug (Phase 4F)
- **Problem**: Products existed in multiple categories, causing duplicates and UI bloat. Legacy heuristics forced 1:1 mapping.
- **Experiment**: Upgraded Schema to support M:N `product_memberships` and introduced `CATEGORY`, `COLLECTION`, and `UNKNOWN` classifiers based on aisle_type.
- **Result**: 100% of products were successfully contextualized without duplicate price observations.

## Commercial Integrity (Phase 4G)
- **Problem**: Rappi combines Public discounts, Pro-exclusive discounts, NxM bundles, and Progressive pricing in confusing nested JSON arrays.
- **Experiment**: Split `discount_effective` and `pro_discount_effective`. Implemented mathematical deduction for Progressive deals rather than string matching.
- **Result**: Perfect separation. A product can now display a baseline Public discount alongside an enhanced Pro discount. (0 = no Pro, 1 = Pro observed, NULL = unknown).

## Alerts & Longitudinal Idempotency (Phase 4H & 4I)
- **Problem**: Running crawls generates massive event noise. `OUT_OF_STOCK` and `PRICE_DROP` oscilations would spam the user.
- **Experiment**: Built `DealWatcher`, an idempotent SQL engine that compares historical tuples, and implemented a strict Canary Watch limit (High-Signal only).
- **Result**: Successfully compressed 7k+ historical observations into 0 retro-spam notifications, whilst correctly evaluating 80 legitimate `NEW_PRODUCT_WITH_DEAL` / `NEW_DEAL` events for Termux delivery. 

## Conclusion
The Rappi integration is complete. By establishing Android as the Primary Operational Authority and Web as the Secondary Structured Oracle, DealHunter achieved total operational maturity. The crawler runs reliably on Termux `crond` 4x a day without destroying the database or leaking secrets.
