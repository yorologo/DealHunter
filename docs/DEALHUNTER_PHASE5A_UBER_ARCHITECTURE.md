# DEALHUNTER PHASE 5A: UBER EATS ARCHITECTURE ANALYSIS

This document details the architectural impact of integrating Uber Eats as the second provider in DealHunter v3.0.1.

## 1. Provider Boundaries

### 1.1 PROVIDER_NEUTRAL Modules
- **`dealhunter.db`**: SQLite definitions and transactions. Schema v14 is robust enough to hold data generically.
- **`dealhunter.price_intelligence` / `dealhunter.score`**: Mathematical models for detecting `REAL_DEAL` and target anomalies. Operates strictly on `observations` table data.
- **`dealhunter.query_layer`**: Faceted search layer. Agnostic to where data originated.
- **`dealhunter.alerts_engine`**: Triggers notifications based on DB price drops.
- **`dealhunter.scheduler`**: The `flock` and cron mechanisms are completely generic.
- **`dealhunter.web.routes` & `dealhunter.web.queries`**: Most endpoints simply query the DB. 

### 1.2 RAPPI_SPECIFIC Modules
- **`dealhunter.api`**: Contains all HTTP request logic, payload structures, and header parsing for Rappi.
- **`dealhunter.auth`**: Manages the `Bearer` session token, highly coupled to Rappi's auth headers and endpoints.
- **`dealhunter.catalog_sync`**: Contains logic specific to Rappi's `A5`, `Turbo`, and `Market` pagination payloads.
- **`dealhunter.web.rappi_native`**: Generates Rappi intent URLs.

### 1.3 MIXED Modules
- **`dealhunter.crawler` & `dealhunter.crawler_zone`**: They orchestrate the crawling process, iterating over coordinates, but they currently instantiate Rappi-specific API clients directly.
- **`dealhunter.cli`**: `dealwatcher run` assumes Rappi is the only target.
- **`dealhunter.web.admin`**: Contains Rappi session diagnostic forms.

### 1.4 Concept Leakage
- **`has_pro_offer` / `pro_price`**: Explicitly named after "Rappi Pro", but conceptually represents a "Conditional Premium Subscription".
- **`deal_status = RAPPI_PROMO`**: Hardcoded Rappi nomenclature in generic enums.
- **Toppings / Modifiers**: Concepts mapped from Rappi's restaurant payloads. Uber Eats uses similar concepts, but the mapping logic is currently highly specific to Rappi.

## 2. Core Architecture Analysis

### 2.1 Identity (Store & Product)
Currently, `store_id` (INT or STRING) and `product_id` (STRING) are treated universally. Since Rappi IDs are numeric strings (e.g., `"900123"`), there is a high risk of collision if Uber Eats also uses sequential numeric IDs.
**Impact**: We must namespace IDs.

### 2.2 Namespace Impact
A prefix like `RAPPI-` and `UBER-` (or `UE-`) is required. 
Since SQLite uses loosely typed strings, converting `store_id` from `900123` to `RAPPI-900123` requires a migration, or we can assume backwards compatibility by treating un-prefixed IDs as Rappi, and newly ingested Uber IDs as `UE-900123`.

### 2.3 PUBLIC / PRO Generalization
Uber Eats features **Uber One**. The DB schema already has `pro_price` and `has_pro_offer`.
Instead of renaming columns (which breaks Schema 14), we can generalize the *concept* to **CONDITIONAL**. The UI can map `pro_price` to "Uber One" when `store_id` starts with `UE-`.

### 2.4 Taxonomy
Categories and collections in v3 are structured. Uber Eats categories must map to `category_name`. `is_restaurant` will apply seamlessly to Uber Eats food delivery.

### 2.5 Snapshot Completeness
Rappi endpoints return complete catalogs for Market stores. We must verify if Uber Eats allows full catalog extraction or if it relies heavily on query-based dynamic loading, which could impede `discover` vs `update` logic.

### 2.6 Query Layer
Unaffected. Facets will dynamically adapt to the available providers.

### 2.7 Web Routes (24 Routes)
Unaffected for data retrieval. However, deep-linking components (`product_card.html`, `store_detail.html`) must use a dynamic router that checks the `store_id` namespace to point to `uber_native.py` vs `rappi_native.py`.

### 2.8 Alerts & Scheduler
Unaffected. The scheduler will simply need to trigger two separate sync commands (e.g., `dealwatcher run --provider rappi` and `--provider uber`).

### 2.9 Deeplinks
Requires a new `dealhunter.web.uber_native` module.

### 2.10 Quick Start
Needs an optional step to configure Uber Eats (session/auth).

### 2.11 Security Boundaries
Uber Eats uses its own authentication mechanism (likely different cookies, tokens, or WAF challenges). `dealhunter.uber_auth` must be isolated from `auth.py`.

### 2.12 DB Schema 14
No changes required if we adopt a Thin Acquisition Adapter with ID Namespacing.
