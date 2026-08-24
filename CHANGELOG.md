# Changelog

## v3.0.0-rc1 - 2026-08-24

### Merchant Discovery
- A5 primary CPG discovery
- safe fallback
- scope-safe reconciliation

### Faceted Taxonomy
- M:N memberships
- CATEGORY/COLLECTION/UNKNOWN
- structured aisle_type enrichment

### Commercial Intelligence
- PUBLIC/PRO separation
- NxM
- Progressive
- price integrity

### Web
- dynamic facets
- multiselect
- PUBLIC/PRO
- optimized queries

### Alerts
- temporal transitions
- idempotent alert_events
- canary Watch
- Termux delivery

### Operations
- scheduler 07/10/13/19
- flock
- backups
- longitudinal validation

### Database
- schema evolution 9 → 14


## v2.9.5 - 2026-08-23

### Added
- **Onboarding Experience**: Añadido `docs/VERY_EASY_QUICK_START.md`, un flujo 100% automatizado por IA (Codex/Antigravity) que permite instalar y configurar DealHunter en Termux sin conocimientos de Linux ni comandos.
- **Universal Extraction Contract**: Refactorizado el parser de catálogos y menús de Rappi en `CPGCatalogAdapter` y `RestaurantMenuAdapter`. La nueva búsqueda recursiva (`is_product`) detecta estructuralmente cualquier producto válido en todo el árbol JSON (aisles, components, fallback), eliminando el 100% de los falsos *parser misses* reportados.
- **CSR Bypass**: Se fuerza la carga de SSR inicial mediante `?csr=false` para cadenas masivas como City Market y Farmacias Benavides.
- **Unavailable Detection**: El crawler detecta y clasifica correctamente redirecciones como `tipo/market` o `restaurantNotFound` marcando los stores como `LEGITIMATE_EMPTY` o `UNAVAILABLE`.
- Corrección del `RestaurantMenuAdapter` confirmada mediante validación End-to-End para extraer correctamente los menús de restaurantes como Popeyes y Popeyes Turbo sin fallar ni omitir productos.
- Mejoras a la observabilidad en la página de detalle de Run: se reporta por separado el número de tiendas procesadas vs los productos insertados vs las tiendas fallidas/saltadas.
- Integración de `run_metadata` en SQLite para registrar internamente estadísticas detalladas de descubrimiento (merchants discovered, attempted, completed, failed, y requests generadas).
- Sistema de automatización diaria (Daily Sweep) programable a las 10:00 a.m., integrado con `cron` y la interfaz Web (Catalog Sync), e implementando bloqueos (`flock`) para evitar concurrencia.

## v2.9.4 - 2026-08-22

Patch release enfocado en la estabilización de la interfaz de administración web y comportamiento del crawler asíncrono:
- La página de detalle del run (Run Detail) muestra el modo del crawler de forma explícita y su nivel de cobertura.
- Se implementó HTMX para refrescar la lista de ejecuciones y el detalle automáticamente cada 3 a 5 segundos mientras el crawler está activo.
- Se previenen ejecuciones múltiples simultáneas del crawler web (`double-submit` a nivel servidor y JS).
- El endpoint `/admin/runs` ya no muta la base de datos para intentar reconciliar ejecuciones, eliminando efectos secundarios de solo lectura.
- El servidor web lanza el proceso del crawler como una sesión independiente, permitiendo que el crawler termine exitosamente incluso si el servidor web se reinicia.
- Uso de `INSERT OR IGNORE` en la inicialización de ejecuciones mediante CLI para prevenir duplicaciones o conflictos con la Web UI.
- Mejor manejo del token CSRF con un mensaje claro humano para errores CSRF genuinos (y preservando otros errores HTTP 400).
- Fallback a redirección HTTP normal cuando las peticiones como la creación de runs o syncs provienen de clientes que no envían cabeceras de HTMX.
- Corregida etiqueta de métricas a "Tiendas conocidas en inventario" para clarificar semántica vs tiendas descubiertas.

## v2.9.3

Patch release enfocado en:

- autenticación positiva usando Unified Search;
- eliminación del falso UNVERIFIED causado por `/profile` WAF;
- semántica segura 401 / 403 / 429 / timeout;
- payload canónico;
- `eta` como evidencia positiva, no negativa;
- crawler_mode persistido al inicio;
- metadata correcta en runs parciales/abortados.

## v2.9.2
Patch release.
- persistencia del estado de validación;
- source de sesión consistente;
- Account Check observable;
- wizard Save and Check real;
- estados UNVERIFIED / VALID / EXPIRED;
- coherencia cross-page;
- Web crawler action fix (PYTHONPATH propagado correctamente);
- corrección de runs silenciosos (0s) al usar botón Web.

## [Unreleased]
- feat: Deal Score V1 stabilization and Deal/Market Advantage isolation
- feat: Advanced Restaurant Taxonomy extraction directly from NextJS metadata
- feat: Native multiselect filtering (UNION logic) for Stores and Categories
- feat: Price Integrity Engine (glitch detection, currency mismatch handling)
- feat: Native Rappi app launcher via directed Android Intent (`am start -p com.grability.rappi`)
- feat: Exact-store Rappi deep links (`gbrappi` + server-side `store_id`) for verified Restaurant, Market and Turbo store types through Shizuku
- feat: Run-level capture provenance and explicit local `lat/lng` configuration with non-destructive location-change warnings
- fix: Replace `termux-open-url` (browser) with package-targeted Intent for "Abrir en Rappi"
- fix: Remove the hardcoded CDMX crawler fallback and the false-success Rappi Home/website fallbacks
- fix: Make the installed 07:00/10:00/13:00/19:00 cron consume the same canonical location configuration
- fix: Elimination of hardcoded 65% discount arbitrary limits
- fix: Structured taxonomy enforcement and robust URL fallback resolution

## [2.9.1] - 2026-08-22

Patch release de estabilidad y UX para Zone Inventory y Session Management.

### Fixed / UX
- SessionStatus canónico: unifica la validación y gestión de estados de sesión.
- Clarificación de estados `CONFIGURED` vs `VALID`.
- Conservación de sesiones `EXPIRED` en persistencia (sin borrar el archivo cifrado local).
- Semántica robusta de 401/403/WAF.
- Estado `UNVERIFIED` para fallos de red o WAF ambiguos.
- Nuevos estados en Catalog Sync: `READY`, `ACTIVE`, `PARTIAL`.
- Restauración de un wizard Web completamente funcional.
- Recuperación del procedimiento V7 de sesión (Omni-Interceptor de AJAX).
- Eliminación de instrucciones obsoletas y fallidas (basadas en localStorage).
- Consolidación del Source de sesión para que refleje correctamente el almacenamiento persistente cifrado.
- Corrección de visualización de timestamps a formato local en toda la UI.
- Mejoras a la experiencia (UX) de los resultados legacy run.
- Adición de la versión visible en tiempo de ejecución (footer de base.html) para identificar servidores huérfanos.
- Ampliación sustancial del conjunto de pruebas para respaldar la estabilidad (277 tests).

## [2.9.0] - 2026-08-22

### Added
- Zone Inventory mode using authenticated `catalog_sync`.
- Automatic crawler strategy: switches to `ZONE_INVENTORY` on valid session, fallbacks to `SEARCH_DISCOVERY` on missing/expired session.
- Run coverage metadata (`crawler_mode`, `coverage_complete`).
- Store lifecycle reconciliation (`status`, `last_seen_at`) marking missing stores as `STALE`.
- Product availability reconciliation marking missing products as `UNAVAILABLE`.
- 401 fallback mechanism that cleanly aborts partial runs and restarts via Search Discovery.
- `BACK_IN_STOCK` seamless integration via Alerts Engine.
- Schema upgraded to v8.
- Doctor check enhancements for Crawler Mode and Session.
- Catalog Sync UX improvements showing active mode and coverage limits.

## [2.8.2] - 2026-08-21

### Reliability (Background Runtime)
- fix: DealHunter ya no libera `termux-wake-lock` automáticamente al salir, previniendo la terminación no intencionada de otros procesos Termux de fondo (ej. sshd).
- feat: Doctor informa correctamente que el Wake Lock es compartido a nivel de aplicación Termux.
- docs: documentada la necesidad de `termux-wake-unlock` manual.

## [2.8.1] - 2026-08-21

### Background Runtime
- DealHunter Web adquiere automáticamente Termux Wake Lock al iniciar
- mantiene mejor el servidor activo cuando Termux está en segundo plano
- libera el wake lock en cierre limpio (Nota: esto es global para Termux y podría afectar a otros procesos si ya tenían el lock)
- Doctor muestra el estado de Background Runtime
- no altera automáticamente Doze/AppOps
- Android aún puede matar el proceso por presión extrema de memoria (OOM)

## [2.8.0] - 2026-08-21

### Catalog Sync
- authenticated catalog synchronization
- Admin Web setup
- status/onboarding
- explicit network actions
- Market and Turbo support
- partial/error behavior

### Session Management
- temporary sessions
- environment sessions
- encrypted persistent sessions
- replace/delete
- expired status
- explicit consent
- SecretStore
- FAIL CLOSED

### Security
- no plaintext fallback
- secret isolation
- test sandboxing
- filesystem permissions (0600)

### Reliability
- auth CLI repair
- expanded tests
- clean CI dependency installation

## [2.7.0] - 2026-08-20
- feat: DealHunter Administration Web Interface
- feat: Admin Home with live metrics and system health
- feat: Account diagnostics (read-only, network opt-in via POST)
- feat: Runs list and Run Detail (lat/lng privacy preserved)
- feat: Structured Events/Errors dashboard derived from runs
- feat: Doctor integration with network check via POST
- feat: Database diagnostics and secure backup UI
- feat: Settings UI with config precedence visibility
- feat: SAFE_EDITABLE, READ_ONLY, and SECRET_FORBIDDEN classifications
- feat: CSRF protection on all mutable endpoints
- feat: Secret hardening (secrets are masked and never transmitted to HTML)
- feat: Local-only behavior by default (0 external requests on page loads)

## [2.6.0] - 2026-08-19
- feat: DealHunter Web Foundation (Flask + HTMX + Bootstrap)
- feat: Web Application Shell with responsive Desktop Sidebar & Mobile Bottom Nav
- feat: Theme (Light/Dark/System) & Density preferences
- feat: Offline local frontend assets (Chart.js, Bootstrap, HTMX)
- feat: Product Detail view with multi-tab layout and Historical Price Chart
- feat: Cross-store product comparison anchor matching (`/compare`)
- feat: Local UI Search with grouped results and server-side LIMIT
- feat: Home Dashboard integrating Deals, System Status and Opportunities
- feat: Market, Turbo, and Stores views with robust HTMX pagination
- feat: Restaurants Web Experience with menu grouping and custom dish cards
- feat: structured category metadata from provider (`schema v6`)
- feat: structured has_toppings attribute (`schema v7`) to eliminate NLP heuristics
- feat: local-first, air-gapped security without CDNs or tracking
- fix: unified unit price formatter (`format_unit_price`)

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
