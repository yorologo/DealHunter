# DealHunter Phase 4D - Faceted Web Integration

## Overview
Phase 4D bridges the Faceted Query Layer (from Phase 4C) directly to the Web UI, exposing the new semantic dimensions to the user while preserving mobile-first responsive constraints. 

## Integration Points

### 1. Dynamic Facets (`get_ui_facets`)
Instead of issuing static independent queries to find available stores or categories, the UI now calls `get_ui_facets()` which delegates to `get_facet_counts()` in the `query_layer`. This ensures:
- If a user filters by Store X, the category list immediately updates to show only categories actually populated for Store X.
- New dimensions like Collections and Store Facets are seamlessly integrated into the catalog templates.

### 2. URL State & Multiselect
- All filters (Store, Category, Collection, Facet, Channel) are preserved as query strings.
- HTMX handles partial grid reloads, seamlessly updating the `catalog-grid` and URL history without a full page refresh.
- Selecting 0 items equates to "No Filter".
- The logic strictly enforces Phase 4C semantics: **OR** within the same dimension (e.g. `category=A&category=B`), and **AND** across dimensions (e.g. `category=A&store=X`).

### 3. Commercial UI (Public vs Pro)
- A new **Tipo de Oferta** selector allows toggling between `PUBLIC` (Default), `PRO` (Pro Exclusivo), and `ALL`.
- The product cards and rows have been updated. When a product has a valid Pro offer, it displays a distinct `Pro $XX (-Y%)` badge alongside the standard public price. The public price is never overwritten, maintaining complete transparency.

## Performance Optimization (Schema 13)
During Phase 4D benchmarking, extracting facet counts across 5 subqueries caused the median UI response to climb to ~1400ms on Termux. 

**EXPLAIN QUERY PLAN** revealed the bottleneck was the temporal deduplication window function:
`USE TEMP B-TREE FOR ORDER BY` inside the `ROW_NUMBER() OVER(PARTITION BY store_id, product_id ORDER BY timestamp DESC, ROWID DESC)` clause.

**Resolution:**
We introduced Schema Version 13 with the following index:
`CREATE INDEX IF NOT EXISTS idx_obs_history ON observations(store_id, product_id, timestamp DESC, id DESC)`

**Results (Before vs After):**
- **get_facet_counts (Complex Query)**: Median ~1396ms -> ~730ms.
- **Base Result Queries**: Drop from ~320ms -> ~230ms.

By avoiding the temporary B-Tree sort during the window function, UI responsiveness on mobile Termux is restored to highly interactive levels (< 800ms full reload).

## Partial Population Adherence
The UI seamlessly degrades when faceted data is missing:
- **Category Fallback**: When `product_memberships` (trusted) is unavailable for a store, it falls back to `products.category` (legacy).
- **Collections**: Only rendered when actual collection data is present.
- **Empty States**: Specifically tailored messages inform the user if no products match their current combination.
