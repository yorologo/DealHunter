# Changelog

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
