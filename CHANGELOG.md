# Changelog

## [2.3.0-dev] - Unreleased
- feat: product normalization engine for brand, quantity, and unit extraction
- feat: support metric standardizations (g to kg, ml to L) and pack expansions
- feat: dynamic `unit_price` calculation in historical analyzer
- feat: product fingerprints for robust cross-store and temporal matching
- feat: added `--sort unit-price` support in CLI
- feat: exact and high-confidence product matching logic (no fuzzy yet)
- feat: `compare` command in `rappi-historico` to find best multi-store prices
- test: unit and integration tests for parsing, exact/high/no matches, and cross-store
- docs: `product-normalization.md` and `product-matching.md` specification

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
