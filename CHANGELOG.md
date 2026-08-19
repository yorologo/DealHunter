# Changelog

## [2.7.0-dev] - Unreleased
- feat: DealHunter Web Phase B (Product Detail & Compare)
- feat: `/products/<store_id>/<product_id>` layout with Tabs, History Chart, metrics, and Deal explanation
- feat: `/compare` Cross-Store matching and visual layout with Best Store logic
- feat: Client-side historical chart using local Chart.js with ranges
- feat: Basic Products catalog and Breadcrumbs

## [2.6.0-dev] - Unreleased
- feat: DealHunter Web Foundation (Flask + HTMX + Bootstrap)
- feat: Web Application Shell with Desktop Sidebar & Mobile Bottom Nav
- feat: Theme (Light/Dark/System) & Density preferences
- feat: Local UI Search with `LIMIT`
- feat: Home Dashboard integrating deals and system status
- feat: `--port` argument in `bin/rappi-historico web`

## [2.5.0] - 2026-08-19
- feat: DealHunter v2.5 Alerts Engine
- feat: local notification evaluation (TARGET_PRICE, NEW_LOW, REAL_DEAL, PRICE_DROP, BACK_IN_STOCK)
- feat: deduplication and SEEN/NEW persistence in SQLite
- feat: CLI commands (`alerts list`, `alerts evaluate`, `alerts mark-seen`)

## [2.4.0] - 2026-08-19
- feat: historical price intelligence
- feat: median_30d, historical min/max/average, previous price, price change metrics
- feat: Deal classifications (NEW_LOW, REAL_DEAL, GOOD_PRICE, INSUFFICIENT_HISTORY)
- feat: suspicious reference price detection
- feat: cross-store historical comparison
- feat: best current store and best unit price identification
- feat: explainable reasons for deal status
- feat: `deals` subcommand in CLI

## [2.3.0] - 2026-08-19
- feat: product normalization engine (brand, quantity, unit, and pack count)
- feat: support metric standardizations (g to kg, ml to L) and pack expansions
- feat: dynamic unit pricing calculation (`unit_price`)
- feat: conservative fingerprints for robust cross-store matching
- feat: `compare` command in `rappi-historico` to find best multi-store prices
- feat: EXACT, HIGH_CONFIDENCE, and FUZZY fallback product matching logic
- fix: hardened semantic safeguards for size/pack/variant mismatches
- docs: documented current provider brand limitation (unified-search) and UPSERT readiness

## [2.2.0] - 2026-08-19
- feat: structured error handling with error catalog and classification
- feat: partial run support (preserves committed observations on failure)
- feat: minimal checkpoint model for crawl progress tracking
- feat: `rappi-ofertas doctor` diagnostic command
- feat: provider placeholders (Turbo, Restaurants, Account context)
- feat: full integration of **Rappi Turbo** as a first-class vertical
- feat: initial support for **Restaurants** menus and promotions
- feat: strictly read-only, sanitised account diagnostics via `rappi-ofertas account status`
- test: robustness tests, turbo offline tests, restaurant tests, account privacy tests
- docs: error-handling.md, turbo.md, restaurants.md, account-diagnostics.md

## [2.1.0] - 2026-08-18
- feat: persistent configuration (`config.toml`)
- feat: profiles
- feat: advanced filters (`--min-discount`, `--max-price`, `--only-nxm`)
- feat: discover/update crawling modes
- feat: historical price filtering (`--new-low`, `--price-drop`)
- feat: watchlist
- feat: price targets
- feat: multiple output formats (`table`, `json`, `csv`, `markdown`)
- feat: DB utilities (`db integrity`, `db vacuum`, `db backup`, `db status`)

## v2.0.0 — Historical Tracking
* Motor `rappi-historico` añadido para combatir manipulación de *precios originales*.
* Reestructuración DB: Adición de `runs` e identificador de sesiones temporales.
* Deduplicación de `observations` usando la clave compuesta `(run_id, store_id, product_id)`.
* Detección algorítmica de estados (`NEW_LOW`, `REAL_DEAL`, `GOOD_DEAL`, `RAPPI_PROMO`).

## v1.0.0 — Deal Hunter Crawler
* Refactorización de Accesibility/UI Automator a API `unified-search`.
* Búsqueda estrucutrada con colas adaptativas.
* Implementación de motor matemático para normalizar promociones `NxM`.
* Soporte nativo para SQLite (`rappi-deals.db`).

## v0.1.0 — Research / PoC
* Pruebas de concepto vía logcat y Shizuku.
* Inspección de SDUI en Flutter/Dart.

## [v2.6.0] - Unreleased
- **Feat**: Restaurants Web Experience (Phase B3) con menu grouping, dish cards, y manejo correcto de availability y precio base (toppings).
- **Fix**: Schema v6 introduces `category` column to products table for true semantic taxonomy, replacing query_term fallbacks.
