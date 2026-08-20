# AGENTS.md — DealHunter

## Project Mission

DealHunter is a local-first, read-only price intelligence tool.

Its purpose is to discover, validate and compare deals inside Rappi and progressively across other retailers/sources in order to answer:

- What is actually a good deal?
- Where is a product cheapest?
- Is the advertised discount real compared with historical prices?
- When is the best time to buy?
- Which store/source provides the best real value?

DealHunter must evolve toward:

Discovery
→ Promotion validation
→ Price history
→ Product normalization
→ Cross-store comparison
→ Cross-source comparison
→ Purchase intelligence

The project must prioritize demonstrable value, not the largest advertised discount.

---

## CURRENT STABLE

- **Version**: v2.7.0
- **Schema**: 7

### Web Modules Status:
- **COMPRAR**: Completado (Deals, Market, Turbo, Restaurants, Categories, Stores)
- **INVESTIGAR**: Completado (Products, Detail, History, Compare)
- **SEGUIR**: Watchlist y Alerts Engine operativos en Core/CLI. Interfaz web pendiente para v2.8.
- **ADMINISTRAR**: Completado (Admin Home, Account Diagnostics, Runs, Events, Doctor, Database Backup, Settings)

## Core Technical Rules Stabilized:
- **Categories**: Structured category only (`products.category` from `category_name`), no heuristics.
- **Toppings**: Structured `has_toppings` only, no NLP inference on names.
- **Comparison**: Anchor compare (Precision-first, SQL limits candidates, `compute_match` decides).
- **Formatters**: Unit-price formatter shared.
- **Admin Network**: Admin GET is local-only (0 external requests). Network diagnostics require explicit POST.
- **Security**: Secrets NEVER passed to templates. Config Settings allowlist (`SAFE_EDITABLE`). CSRF required for POST. DB actions limited to safe read/backup.
- **Location context**: Crawls require explicit `lat/lng` from CLI/profile/global config. Never restore a hardcoded city fallback. Persist provenance once per `runs` row; a significant change warns and preserves history until an explicit, backed-up decision.
- **Rappi navigation**: Resolve `store_id` and type server-side, use the verified `gbrappi` exact-store contract through Shizuku, and keep `com.grability.rappi` fixed. Browser, website and Home fallbacks are forbidden. Unsupported types fail closed.
- **UI/OCR boundary**: Android hierarchy, screenshots or OCR may support account/zone diagnostics and manual navigation verification only. They are not a normal product/price crawler and temporary sensitive artifacts must be discarded.

### 1. Local-first

User data, configuration, SQLite history, watchlists and analysis should remain local whenever possible.

Do not introduce cloud infrastructure unless it provides a clear and justified benefit.

### 2. Read-only

DealHunter analyzes information.

It must not:

- place orders;
- modify orders;
- change account settings;
- apply payment methods;
- alter addresses;
- move money;
- redeem benefits automatically.

### 3. Privacy by design

Never persist:

- passwords;
- authentication tokens;
- cookies;
- Authorization headers;
- session secrets;
- payment data;
- addresses;
- sensitive account identifiers;
- unnecessary personal data.

Account information may only be queried when explicitly useful for diagnostics/context.

Account diagnostics must follow:

query
→ sanitize
→ display
→ discard

Do not persist account data.

### 4. Explainable results

DealHunter must be able to explain why an item received a classification or score.

Prefer:

REAL_DEAL
Historical median: $100
Current price: $45
Historical discount: 55%
Observations: 30
Confidence: HIGH

over opaque scoring.

### 5. Conservative conclusions

Never manufacture confidence.

If historical data is insufficient, return:

INSUFFICIENT_HISTORY

instead of guessing.

### 6. Respect external services

- minimize requests;
- reuse cached/local data;
- honor request budgets;
- use conservative retry/backoff;
- stop appropriately on rate limiting;
- do not implement anti-bot bypasses;
- do not evade HTTP 429 / Cloudflare limits.

---

## Current Stable Release

Current public stable baseline:

DealHunter v2.1.0

Main capabilities include:

- persistent TOML configuration;
- profiles;
- advanced filtering;
- custom minimum discounts;
- product queries;
- store filters;
- vertical filters;
- price filters;
- promotion filters;
- discover/update modes;
- historical observations;
- watchlists;
- target prices;
- JSON/CSV/Markdown/table output;
- SQLite utilities;
- run history;
- offline tests;
- Termux support.

Preserve backwards compatibility unless a breaking change is clearly justified.

---

## Discount Rules

Direct price discount:

discount_price =
(1 - price / original_price) * 100

NxM promotion:

discount_promotion =
(1 - units_condition / promotion_value) * 100

Examples:

- 2x1 = 50.00%
- 3x1 = 66.67%
- 3x2 = 33.33%
- 4x2 = 50.00%

Effective discount:

discount_effective =
max(discount_price, discount_promotion)

Never add incompatible discounts together.

Do not classify 3x2 as 50%.

---

## Historical Price Principles

Historical analysis must rely on observed prices, not only platform-provided original_price.

Relevant concepts include:

- previous_price;
- median_7d;
- median_30d;
- historical_min;
- historical_max;
- historical_discount;
- NEW_LOW;
- GOOD_DEAL;
- REAL_DEAL;
- INSUFFICIENT_HISTORY.

Do not use original_price as a substitute for historical evidence.

Keep promotion state conceptually separate from historical state.

Example:

promo_status = RAPPI_PROMO
history_status = NORMAL

is valid.

---

## SQLite Rules

SQLite is the local source of truth.

Preserve:

- stores;
- products;
- runs;
- observations;
- watchlist;
- schema_version;
- existing historical observations.

Important identity:

store_id + product_id

identifies a product within a store.

Historical observations must allow multiple runs while preventing duplicates inside the same run.

Expected uniqueness:

UNIQUE(run_id, store_id, product_id)

Migrations must be:

- safe;
- idempotent;
- backed up first;
- tested on temporary databases.

Never destructively migrate the user's real database without a backup.

---

## Discover vs Update

Keep these concepts separate.

### discover

Used to find:

- new stores;
- new products;
- brands;
- categories;
- search opportunities.

May use adaptive discovery and novelty/saturation logic.

### update

Used primarily to refresh:

- known products;
- prices;
- promotions;
- availability;
- historical observations.

Prefer update for frequent historical collection.

Prefer discover less frequently.

---

## Product Intelligence Direction

Future product comparison should not rely on fuzzy string matching alone.

Normalize products using attributes such as:

- brand;
- normalized name;
- variant;
- quantity;
- unit.

Example:

"Coca Cola Original PET 2000 ml"

should ideally normalize toward:

brand = coca-cola
variant = original
quantity = 2
unit = L

Prefer normalized product fingerprints before fuzzy matching.

Potential matching states:

- EXACT_MATCH
- HIGH_CONFIDENCE_MATCH
- POSSIBLE_MATCH
- NO_MATCH

Never silently compare clearly different products.

---

## Unit Pricing

Future comparison should support normalized quantities such as:

- g;
- kg;
- ml;
- L;
- piece;
- tablet;
- capsule;
- pack.

Examples:

2000 ml → 2 L

Then calculate appropriate unit prices such as:

- MXN/kg;
- MXN/L;
- MXN/piece;
- MXN/tablet.

Unit pricing is a priority for reliable cross-store comparison.

---

## Rappi Coverage Direction

DealHunter should progressively cover useful Rappi verticals including:

- supermarkets;
- pharmacies;
- pets;
- technology;
- home;
- baby;
- hygiene;
- liquor;
- Rappi Turbo;
- restaurants;
- other useful verticals discovered later.

Do not assume every vertical uses the same data model.

Use adapters/modules when needed.

---

## Turbo

Turbo should eventually be treated as a first-class vertical.

Desired capabilities:

- catalog discovery;
- prices;
- promotions;
- availability;
- quantity/unit normalization;
- history;
- comparison with other stores.

---

## Restaurants

Restaurant support may include:

- restaurants;
- menus;
- menu items;
- combos;
- prices;
- promotions;
- availability;
- historical price observations.

Keep restaurant products conceptually distinct from normal retail SKUs where necessary.

---

## Account Diagnostics

Account information is NOT a primary DealHunter data source.

It may only be used for read-only diagnostics/context, for example:

- session health;
- market/region;
- membership status;
- benefits context;
- promotion eligibility context.

Possible future command:

dealhunter doctor

Desired output may include:

- connectivity;
- database health;
- provider health;
- account/session status;
- membership status;
- last successful run.

Never persist sensitive account information.

---

## Error Handling

Errors should become structured, understandable states.

Examples:

- NETWORK_ERROR
- TIMEOUT
- HTTP_429
- CLOUDFLARE_LIMIT
- INVALID_RESPONSE
- PARSER_ERROR
- DB_LOCKED
- DB_CORRUPT
- CONFIG_ERROR
- PARTIAL_RUN
- REQUEST_BUDGET_REACHED

Prefer errors with:

- code;
- category;
- human-readable message;
- recoverable flag;
- recommended action.

Retries must remain conservative.

Do not aggressively retry 429/1015 responses.

---

## Partial Runs and Recovery

A failed/interrupted run should preserve already committed valid observations.

Where useful, use:

- PARTIAL status;
- checkpoints;
- completed-query tracking;
- safe resume behavior.

Never corrupt historical data just because a run was interrupted.

---

## Testing Requirements

Every meaningful new feature must include tests.

Prefer offline tests with fixtures/mocks.

CI must not make real Rappi requests.

Priority test areas:

- discount math;
- configuration precedence;
- filtering;
- product normalization;
- historical analysis;
- SQLite;
- migrations;
- CLI;
- watchlists;
- error handling;
- provider adapters;
- product matching.

Use temporary HOME / XDG_CONFIG_HOME / SQLite databases during tests.

Never test destructively against the user's real configuration or database.

---

## Configuration Precedence

Configuration priority must remain:

CLI
>
Profile
>
Global config
>
Internal defaults

CLI always wins.

Global configuration normally lives under:

~/.config/dealhunter/config.toml

or XDG_CONFIG_HOME.

Do not automatically persist personal coordinates without explicit user intent.

---

## Output Rules

Human and machine-readable output should remain separate.

Supported/desired formats include:

- table;
- compact;
- JSON;
- CSV;
- Markdown.

Machine-readable stdout must not be polluted with operational logs.

Send logs to stderr when appropriate.

---

## Git and Security

Never commit:

- real SQLite databases;
- DB backups;
- personal configuration;
- real API responses;
- logs;
- cookies;
- tokens;
- credentials;
- APK dumps;
- Blutter output;
- PII;
- personal coordinates;
- temporary files.

Keep `.gitignore` updated as the project evolves.

Sanitized fixtures/examples are allowed.

Before public commits/releases:

- run tests;
- inspect git status;
- inspect tracked files;
- audit secrets/PII;
- ensure working tree is clean.

Never rewrite public tags.

Never force-push unless the user explicitly requests it and understands the consequences.

---

## Documentation Rules

When adding or changing a feature, update relevant documentation:

- README.md;
- docs/;
- CLI --help;
- examples;
- tests;
- CHANGELOG when appropriate.

Documentation must describe real behavior.

Do not document planned features as implemented.

Code + SQLite schema are the source of truth when documentation disagrees.

---

## Development Style

Follow KISS.

Do not perform giant refactors when a small change is enough.

Preferred workflow:

inspect
→ implement one coherent feature
→ test
→ validate
→ document
→ commit

Avoid unnecessary dependencies.

Termux/Android remains a priority environment.

Keep the Python core portable where practical.

---

## Agent Behavior

Before modifying DealHunter:

1. inspect existing implementation;
2. identify whether the feature already exists;
3. preserve compatibility;
4. choose the smallest reasonable change;
5. add/update tests;
6. test offline first;
7. use real network only for minimal controlled validation when necessary;
8. update documentation;
9. inspect git diff;
10. do not push unless explicitly instructed.

Do not claim success without executed validation.

Never use estimated crawler results as confirmed data.

SQLite committed data is the source of truth for reported counts.

---

## Roadmap

### v2.1 — Released

Completed:

- configuration;
- profiles;
- filters;
- discover/update;
- historical tracking;
- watchlist;
- price targets;
- output formats;
- DB utilities;
- documentation;
- tests.

### v2.2 — Rappi Coverage & Robustness

Priority direction:

- Rappi Turbo;
- restaurants;
- availability;
- structured error handling;
- partial runs;
- checkpoints;
- doctor/health checks;
- read-only account diagnostics;
- improved sanitized logging.

### v2.3 — Product Intelligence

Priority direction:

- brand normalization;
- quantity parsing;
- unit normalization;
- unit prices;
- product fingerprints;
- matching confidence;
- cross-store product matching.

### v2.4 — Price Intelligence

Priority direction:

- cross-store comparison;
- best current price;
- historical comparison;
- confidence score;
- improved deal score;
- price anomalies;
- suspicious reference price detection;
- availability history.

### v3.0 — Multi-source Intelligence

Long-term direction:

- additional retailers/providers;
- cross-source product matching;
- basket optimization;
- effective purchase cost;
- alerts;
- daily digest;
- local API;
- dashboard.

---

## Feature Decision Checklist

Before implementing a new idea, consider:

- Does it help find better deals?
- Does it improve price comparison?
- Does it improve data confidence?
- Does it reduce unnecessary requests?
- Does it improve robustness?
- Does it preserve privacy?
- Can it be tested?
- Can its result be explained?

Prefer features that satisfy several of these criteria.

---

## Master Rule

DealHunter must not chase the biggest advertised discount.

DealHunter must find the best value that can be demonstrated with data.

Goal:

WHAT TO BUY
+
WHERE TO BUY
+
WHEN TO BUY

---

# Web Application & UX Architecture

## Strategic Direction

DealHunter's next major evolution is a local web application for shopping and price intelligence.

The web interface must NOT be treated as a graphical wrapper around SQLite or the CLI.

Its primary purpose is to help the user answer:

1. What is worth buying today?
2. Where is it cheapest right now?
3. Is the advertised deal actually good according to historical data?
4. How has the price changed over time?
5. What changed since the user's last visit?
6. Is DealHunter itself operating correctly?

The interface must preserve the existing principles:

- local-first
- privacy-first
- explainable
- conservative
- KISS
- offline-capable
- lightweight
- Termux/Android friendly
- no duplicated domain logic

## Primary Information Architecture

The UI is organized into four major functional areas:

### COMPRAR

Focused on discovering what is worth buying now.

Primary views:

- Inicio
- Oportunidades
- Supermercados
- Turbo
- Restaurantes
- Categorías

### INVESTIGAR

Focused on understanding products, prices and stores.

Primary views:

- Productos
- Tiendas
- Comparador
- Histórico

### SEGUIR

Focused on products and conditions the user wants to monitor.

Primary views:

- Watchlist
- Alertas

### ADMINISTRAR

Focused on DealHunter itself.

Primary views:

- Cuenta Rappi
- Actividad / Runs
- Errores / Eventos
- Doctor
- Base de datos
- Configuración

Do not flatten all pages into one large navigation menu if hierarchy provides a clearer experience.

## Contextual Views

The application must support contextual drill-down views for:

- Category
- Store
- Product

Navigation should naturally support flows such as:

Inicio
→ Oportunidad
→ Categoría
→ Producto
→ Comparar tiendas

and:

Supermercados
→ Tienda
→ Categoría
→ Producto
→ Histórico

Use breadcrumbs for deep navigation when useful.

## Home

Home should answer:

"What is worth buying today?"

Prioritize:

- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- meaningful price drops
- target prices reached
- back-in-stock events
- best current cross-store opportunities
- watched products
- useful category discovery

Administrative statistics should remain secondary.

Preferred information hierarchy:

DECISION
→ EXPLANATION
→ COMPARISON
→ TECHNICAL DATA

## Opportunities

Provide a dedicated opportunities view supporting:

- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- PRICE_DROP
- TARGET_PRICE
- BACK_IN_STOCK
- SUSPICIOUS_REFERENCE_PRICE

Useful filters include:

- vertical
- category
- store
- availability
- price
- deal status

Useful sorting includes:

- best opportunity
- lowest current price
- lowest unit price
- largest real price drop
- largest discount vs median
- newest historical low
- most recent

Do not invent opaque ranking systems when existing explainable metrics are sufficient.

## Vertical Views

Maintain distinct views for:

### Supermercados

Represents Market stores and products.

### Turbo

Uses shared components where appropriate but remains a distinct vertical.

Cross-store comparisons against Market products may be shown when safe matching exists.

### Restaurantes

Must use restaurant-appropriate UX rather than supermarket product UX.

Restaurant pages should be restaurant/menu oriented.

When `has_toppings` or modifiers exist and only base price is known, explicitly identify displayed prices as base prices.

Do not imply modifier-inclusive totals when they are unavailable.

## Categories

Categories should be a first-class exploration mechanism.

Use provider category metadata when available.

Do not invent a complex universal taxonomy during the first web implementation.

A future canonical category mapping may use:

provider_category
→ category_alias
→ canonical_category

but this is not required initially.

## Store Detail

A store view may include:

- current product count
- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- categories
- largest price drops
- products increasing in price
- current promotions
- products currently cheaper here than equivalent products in other stores

Do not claim that a store is universally cheaper based only on opportunity counts.

## Product Detail

Product Detail is a highest-priority experience.

It should expose, when available:

- current price
- previous price
- unit price
- availability
- deal status
- reason
- advertised promotion
- median 30d
- historical minimum
- historical maximum
- historical average
- price changes
- observation history
- cross-store comparison

Recommended sections/tabs:

- Resumen
- Histórico
- Comparar
- Observaciones

Historical charts should support useful ranges such as:

- 7D
- 30D
- 90D
- all

Useful reference lines may include:

- current price
- median 30d
- historical minimum

## Cross-Store Comparison

Always distinguish:

- best current store
- historical minimum
- best historical value

`best_store` means the store with the lowest CURRENT comparable price.

Never select today's best store because another store had a lower price in the past.

Show both absolute price and unit price when appropriate.

## Advertised Discount vs Historical Value

The UI must visibly preserve DealHunter's core rule:

The biggest advertised discount is not necessarily the best deal.

When `SUSPICIOUS_REFERENCE_PRICE` is present:

- treat it as a flag
- explain the historical inconsistency
- do not accuse a store of fraud
- do not automatically promote the product to REAL_DEAL

## Watchlist and Alerts

Visually group these under the SEGUIR area while keeping their behavior distinct.

Watchlist may display:

- current price
- target price
- distance to target
- best current store

Alerts may display:

- TARGET_PRICE
- NEW_LOW
- REAL_DEAL
- PRICE_DROP
- BACK_IN_STOCK

Support NEW/SEEN state.

Android system notifications are a future transport layer and must remain decoupled from alert detection logic.

## Account Diagnostics

Provide a read-only Cuenta Rappi diagnostics view.

It may expose only sanitized information such as:

- configured/not configured
- session valid/invalid
- region/market
- membership context
- promotion counts
- last check time

Never expose or persist:

- bearer tokens
- cookies
- personal names
- email
- phone number
- addresses
- payment data
- device identifiers
- sensitive account IDs

Do not provide a web form for persistently saving a Rappi bearer token.

Account network diagnostics must be explicit/opt-in.

Opening the account page must not silently trigger network requests.

## Runs / Activity

Represent execution history as structured activity rather than raw database rows.

Useful run information includes:

- execution type
- timestamp
- duration
- status
- request count
- products processed
- observations created
- partial-run reason
- related structured errors

Support SUCCESS, PARTIAL and FAILED views where applicable.

## Errors / Events

Prefer structured events over raw log dumps.

Useful fields:

- timestamp
- severity
- component
- error code
- run
- sanitized message

Existing structured error codes include:

- NETWORK_ERROR
- TIMEOUT
- HTTP_429
- CLOUDFLARE_LIMIT
- INVALID_RESPONSE
- PARSER_ERROR
- DB_LOCKED
- DB_CORRUPT
- CONFIG_ERROR
- PARTIAL_RUN
- REQUEST_BUDGET_REACHED

Never persist raw API responses merely to support the web event viewer.

Future event storage, if needed, must remain sanitized.

Useful historical views may include:

- errors over time
- HTTP 429 frequency
- timeouts
- partial runs
- errors by vertical

## Doctor

Expose local Doctor health information visually.

Examples:

- Catalog
- Turbo
- Restaurants
- Account
- Database
- SQLite integrity
- schema version
- overall health

Default page loading must use local checks.

Any network diagnostics must require an explicit user action.

## Database Administration

Safe initial actions:

- inspect DB statistics
- inspect schema version
- inspect integrity
- create backup

Avoid destructive database controls in the first web implementation.

Do not expose arbitrary SQL execution.

## Configuration

Separate GLOBAL CONFIGURATION from VIEW PREFERENCES.

Global configuration changes DealHunter behavior.

Possible sections:

- General
- Crawler
- Historical
- Price Intelligence
- Alerts
- Account
- Interface
- Database
- Advanced

Show effective value and configuration source where practical.

Configuration precedence remains:

CLI
> Profile
> Global config
> Internal defaults

Never allow secrets/tokens to be persisted through web configuration.

## View Preferences

View preferences affect presentation only.

Examples:

- filters
- sorting
- page size
- cards/table
- theme
- density

Pure UI preferences should normally use browser localStorage instead of SQLite.

Recommended preferences:

Theme:
- SYSTEM
- LIGHT
- DARK

Density:
- COMFORTABLE
- COMPACT

Product view:
- CARDS
- TABLE

## Search

Provide global search for:

- products
- stores
- restaurants
- categories

Search must be server-side and bounded.

Never load the entire product database into the browser.

A desktop command palette such as Ctrl+K is desirable but optional.

## Saved Views

Future saved views may store useful filter combinations such as:

- NEW_LOW beverages
- REAL_DEAL pharmacy
- cheapest unit-price products

Prefer localStorage initially unless server-side persistence becomes necessary.

## Since Last Visit

A future/useful dashboard feature should summarize meaningful changes since the user's last visit:

- new historical lows
- new real deals
- target prices reached
- price drops
- back-in-stock events

Browser-local last-visit state is preferred initially.

## Global System Status

Provide a compact global status indicator such as:

DealHunter OK

It may summarize:

- last update
- last run
- database health
- account context
- new alerts

Detailed administration remains under ADMINISTRAR.

## Recommended Web Stack

Preferred lightweight stack:

- Python
- Flask
- Jinja2
- HTMX
- Bootstrap 5
- Chart.js

Assets should work locally/offline.

Avoid introducing:

- React
- Vue
- Angular
- Node/npm build pipelines
- SPA complexity

unless a future requirement clearly justifies them.

## Web Architecture

Preferred architecture:

SQLite
→ existing DealHunter domain/services
→ thin web service layer
→ Flask routes
→ Jinja / HTMX
→ browser

The web layer MUST reuse existing logic for:

- normalization
- historical calculations
- Price Intelligence
- matching
- cross-store comparison
- watchlist
- alerts
- configuration

Never implement a separate web-only version of domain rules.

## API Strategy

Do not build a large REST platform unnecessarily.

Small local endpoints are acceptable where useful, for example:

- dashboard
- search
- product history
- compare
- alerts

Prefer server-rendered HTML and HTMX fragments when simpler.

## Performance

The product database already contains tens of thousands of products.

Requirements:

- server-side pagination
- bounded queries
- SQL filtering
- LIMIT
- avoid N+1 queries
- lazy-load expensive charts
- never load the entire product catalog into browser memory
- add indexes only when real measurements justify them

The UI should feel effectively instant during normal localhost navigation.

## Responsive UX

The application must be designed for both desktop and Android/mobile use.

Desktop may use a persistent sidebar.

Mobile should prefer a compact bottom navigation for high-frequency areas such as:

- Inicio
- Deals
- Buscar
- Seguir

Less frequent functions belong in a secondary menu.

Do not merely shrink the desktop UI.

## PWA Direction

The web application should remain compatible with future local PWA support.

Potential future additions:

- manifest
- app icon
- standalone display mode
- theme color

Do not cache sensitive/dynamic database content inappropriately.

## Security

The local web server must bind by default to:

127.0.0.1

Never expose DealHunter to the LAN by default.

Do not serve as static files:

- SQLite databases
- backups
- personal configuration
- tokens
- sensitive logs
- API dumps

Network exposure must require an explicit future configuration decision.

## Web Error UX

User-facing errors should be concise and useful.

Prefer:

"Could not read history.
Code: DB_LOCKED.
Your data has been preserved."

with optional technical details.

Do not show raw stack traces by default.

## Implementation Priority

Implement incrementally.

### Phase A — Foundation

- Flask
- layout/navigation
- responsive shell
- design system
- light/dark
- shared components
- search foundation

### Phase B — Shopping

- Home
- Opportunities
- Supermarkets
- Turbo
- Restaurants
- Categories

### Phase C — Investigation

- Product
- Store
- History
- Compare

### Phase D — Follow

- Watchlist
- Alerts
- since-last-visit summaries

### Phase E — Administration

- Account
- Runs
- Errors/Events
- Doctor
- Database
- Settings

### Phase F — Polish

- PWA
- command palette
- saved views
- mobile polish
- accessibility
- performance audit
- empty/error states

Do not attempt all phases in one large unreviewable implementation.

## UX Master Rule

DealHunter must communicate information in this order:

DECISION
→ EXPLANATION
→ COMPARISON
→ TECHNICAL DATA

The main interface should tell the user what is worth buying and why.

Historical and technical information should remain available for deeper investigation without dominating everyday use.

## Future Scope — Not Immediate

Do not block the web implementation on:

- Android notifications
- brand inference
- inflation adjustment
- prediction
- basket optimization
- external multi-retailer expansion
- AI/LLM matching

These remain future work unless explicitly requested.

EOFcd ~/rappi-deal-hunter

cat >> AGENTS.md <<'EOF'

---

# Web Application & UX Architecture

## Strategic Direction

DealHunter's next major evolution is a local web application for shopping and price intelligence.

The web interface must NOT be treated as a graphical wrapper around SQLite or the CLI.

Its primary purpose is to help the user answer:

1. What is worth buying today?
2. Where is it cheapest right now?
3. Is the advertised deal actually good according to historical data?
4. How has the price changed over time?
5. What changed since the user's last visit?
6. Is DealHunter itself operating correctly?

The interface must preserve the existing principles:

- local-first
- privacy-first
- explainable
- conservative
- KISS
- offline-capable
- lightweight
- Termux/Android friendly
- no duplicated domain logic

## Primary Information Architecture

The UI is organized into four major functional areas:

### COMPRAR

Focused on discovering what is worth buying now.

Primary views:

- Inicio
- Oportunidades
- Supermercados
- Turbo
- Restaurantes
- Categorías

### INVESTIGAR

Focused on understanding products, prices and stores.

Primary views:

- Productos
- Tiendas
- Comparador
- Histórico

### SEGUIR

Focused on products and conditions the user wants to monitor.

Primary views:

- Watchlist
- Alertas

### ADMINISTRAR

Focused on DealHunter itself.

Primary views:

- Cuenta Rappi
- Actividad / Runs
- Errores / Eventos
- Doctor
- Base de datos
- Configuración

Do not flatten all pages into one large navigation menu if hierarchy provides a clearer experience.

## Contextual Views

The application must support contextual drill-down views for:

- Category
- Store
- Product

Navigation should naturally support flows such as:

Inicio
→ Oportunidad
→ Categoría
→ Producto
→ Comparar tiendas

and:

Supermercados
→ Tienda
→ Categoría
→ Producto
→ Histórico

Use breadcrumbs for deep navigation when useful.

## Home

Home should answer:

"What is worth buying today?"

Prioritize:

- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- meaningful price drops
- target prices reached
- back-in-stock events
- best current cross-store opportunities
- watched products
- useful category discovery

Administrative statistics should remain secondary.

Preferred information hierarchy:

DECISION
→ EXPLANATION
→ COMPARISON
→ TECHNICAL DATA

## Opportunities

Provide a dedicated opportunities view supporting:

- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- PRICE_DROP
- TARGET_PRICE
- BACK_IN_STOCK
- SUSPICIOUS_REFERENCE_PRICE

Useful filters include:

- vertical
- category
- store
- availability
- price
- deal status

Useful sorting includes:

- best opportunity
- lowest current price
- lowest unit price
- largest real price drop
- largest discount vs median
- newest historical low
- most recent

Do not invent opaque ranking systems when existing explainable metrics are sufficient.

## Vertical Views

Maintain distinct views for:

### Supermercados

Represents Market stores and products.

### Turbo

Uses shared components where appropriate but remains a distinct vertical.

Cross-store comparisons against Market products may be shown when safe matching exists.

### Restaurantes

Must use restaurant-appropriate UX rather than supermarket product UX.

Restaurant pages should be restaurant/menu oriented.

When `has_toppings` or modifiers exist and only base price is known, explicitly identify displayed prices as base prices.

Do not imply modifier-inclusive totals when they are unavailable.

## Categories

Categories should be a first-class exploration mechanism.

Use provider category metadata when available.

Do not invent a complex universal taxonomy during the first web implementation.

A future canonical category mapping may use:

provider_category
→ category_alias
→ canonical_category

but this is not required initially.

## Store Detail

A store view may include:

- current product count
- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- categories
- largest price drops
- products increasing in price
- current promotions
- products currently cheaper here than equivalent products in other stores

Do not claim that a store is universally cheaper based only on opportunity counts.

## Product Detail

Product Detail is a highest-priority experience.

It should expose, when available:

- current price
- previous price
- unit price
- availability
- deal status
- reason
- advertised promotion
- median 30d
- historical minimum
- historical maximum
- historical average
- price changes
- observation history
- cross-store comparison

Recommended sections/tabs:

- Resumen
- Histórico
- Comparar
- Observaciones

Historical charts should support useful ranges such as:

- 7D
- 30D
- 90D
- all

Useful reference lines may include:

- current price
- median 30d
- historical minimum

## Cross-Store Comparison

Always distinguish:

- best current store
- historical minimum
- best historical value

`best_store` means the store with the lowest CURRENT comparable price.

Never select today's best store because another store had a lower price in the past.

Show both absolute price and unit price when appropriate.

## Advertised Discount vs Historical Value

The UI must visibly preserve DealHunter's core rule:

The biggest advertised discount is not necessarily the best deal.

When `SUSPICIOUS_REFERENCE_PRICE` is present:

- treat it as a flag
- explain the historical inconsistency
- do not accuse a store of fraud
- do not automatically promote the product to REAL_DEAL

## Watchlist and Alerts

Visually group these under the SEGUIR area while keeping their behavior distinct.

Watchlist may display:

- current price
- target price
- distance to target
- best current store

Alerts may display:

- TARGET_PRICE
- NEW_LOW
- REAL_DEAL
- PRICE_DROP
- BACK_IN_STOCK

Support NEW/SEEN state.

Android system notifications are a future transport layer and must remain decoupled from alert detection logic.

## Account Diagnostics

Provide a read-only Cuenta Rappi diagnostics view.

It may expose only sanitized information such as:

- configured/not configured
- session valid/invalid
- region/market
- membership context
- promotion counts
- last check time

Never expose or persist:

- bearer tokens
- cookies
- personal names
- email
- phone number
- addresses
- payment data
- device identifiers
- sensitive account IDs

Do not provide a web form for persistently saving a Rappi bearer token.

Account network diagnostics must be explicit/opt-in.

Opening the account page must not silently trigger network requests.

## Runs / Activity

Represent execution history as structured activity rather than raw database rows.

Useful run information includes:

- execution type
- timestamp
- duration
- status
- request count
- products processed
- observations created
- partial-run reason
- related structured errors

Support SUCCESS, PARTIAL and FAILED views where applicable.

## Errors / Events

Prefer structured events over raw log dumps.

Useful fields:

- timestamp
- severity
- component
- error code
- run
- sanitized message

Existing structured error codes include:

- NETWORK_ERROR
- TIMEOUT
- HTTP_429
- CLOUDFLARE_LIMIT
- INVALID_RESPONSE
- PARSER_ERROR
- DB_LOCKED
- DB_CORRUPT
- CONFIG_ERROR
- PARTIAL_RUN
- REQUEST_BUDGET_REACHED

Never persist raw API responses merely to support the web event viewer.

Future event storage, if needed, must remain sanitized.

Useful historical views may include:

- errors over time
- HTTP 429 frequency
- timeouts
- partial runs
- errors by vertical

## Doctor

Expose local Doctor health information visually.

Examples:

- Catalog
- Turbo
- Restaurants
- Account
- Database
- SQLite integrity
- schema version
- overall health

Default page loading must use local checks.

Any network diagnostics must require an explicit user action.

## Database Administration

Safe initial actions:

- inspect DB statistics
- inspect schema version
- inspect integrity
- create backup

Avoid destructive database controls in the first web implementation.

Do not expose arbitrary SQL execution.

## Configuration

Separate GLOBAL CONFIGURATION from VIEW PREFERENCES.

Global configuration changes DealHunter behavior.

Possible sections:

- General
- Crawler
- Historical
- Price Intelligence
- Alerts
- Account
- Interface
- Database
- Advanced

Show effective value and configuration source where practical.

Configuration precedence remains:

CLI
> Profile
> Global config
> Internal defaults

Never allow secrets/tokens to be persisted through web configuration.

## View Preferences

View preferences affect presentation only.

Examples:

- filters
- sorting
- page size
- cards/table
- theme
- density

Pure UI preferences should normally use browser localStorage instead of SQLite.

Recommended preferences:

Theme:
- SYSTEM
- LIGHT
- DARK

Density:
- COMFORTABLE
- COMPACT

Product view:
- CARDS
- TABLE

## Search

Provide global search for:

- products
- stores
- restaurants
- categories

Search must be server-side and bounded.

Never load the entire product database into the browser.

A desktop command palette such as Ctrl+K is desirable but optional.

## Saved Views

Future saved views may store useful filter combinations such as:

- NEW_LOW beverages
- REAL_DEAL pharmacy
- cheapest unit-price products

Prefer localStorage initially unless server-side persistence becomes necessary.

## Since Last Visit

A future/useful dashboard feature should summarize meaningful changes since the user's last visit:

- new historical lows
- new real deals
- target prices reached
- price drops
- back-in-stock events

Browser-local last-visit state is preferred initially.

## Global System Status

Provide a compact global status indicator such as:

DealHunter OK

It may summarize:

- last update
- last run
- database health
- account context
- new alerts

Detailed administration remains under ADMINISTRAR.

## Recommended Web Stack

Preferred lightweight stack:

- Python
- Flask
- Jinja2
- HTMX
- Bootstrap 5
- Chart.js

Assets should work locally/offline.

Avoid introducing:

- React
- Vue
- Angular
- Node/npm build pipelines
- SPA complexity

unless a future requirement clearly justifies them.

## Web Architecture

Preferred architecture:

SQLite
→ existing DealHunter domain/services
→ thin web service layer
→ Flask routes
→ Jinja / HTMX
→ browser

The web layer MUST reuse existing logic for:

- normalization
- historical calculations
- Price Intelligence
- matching
- cross-store comparison
- watchlist
- alerts
- configuration

Never implement a separate web-only version of domain rules.

## API Strategy

Do not build a large REST platform unnecessarily.

Small local endpoints are acceptable where useful, for example:

- dashboard
- search
- product history
- compare
- alerts

Prefer server-rendered HTML and HTMX fragments when simpler.

## Performance

The product database already contains tens of thousands of products.

Requirements:

- server-side pagination
- bounded queries
- SQL filtering
- LIMIT
- avoid N+1 queries
- lazy-load expensive charts
- never load the entire product catalog into browser memory
- add indexes only when real measurements justify them

The UI should feel effectively instant during normal localhost navigation.

## Responsive UX

The application must be designed for both desktop and Android/mobile use.

Desktop may use a persistent sidebar.

Mobile should prefer a compact bottom navigation for high-frequency areas such as:

- Inicio
- Deals
- Buscar
- Seguir

Less frequent functions belong in a secondary menu.

Do not merely shrink the desktop UI.

## PWA Direction

The web application should remain compatible with future local PWA support.

Potential future additions:

- manifest
- app icon
- standalone display mode
- theme color

Do not cache sensitive/dynamic database content inappropriately.

## Security

The local web server must bind by default to:

127.0.0.1

Never expose DealHunter to the LAN by default.

Do not serve as static files:

- SQLite databases
- backups
- personal configuration
- tokens
- sensitive logs
- API dumps

Network exposure must require an explicit future configuration decision.

## Web Error UX

User-facing errors should be concise and useful.

Prefer:

"Could not read history.
Code: DB_LOCKED.
Your data has been preserved."

with optional technical details.

Do not show raw stack traces by default.

## Implementation Priority

Implement incrementally.

### Phase A — Foundation

- Flask
- layout/navigation
- responsive shell
- design system
- light/dark
- shared components
- search foundation

### Phase B — Shopping

- Home
- Opportunities
- Supermarkets
- Turbo
- Restaurants
- Categories

### Phase C — Investigation

- Product
- Store
- History
- Compare

### Phase D — Follow

- Watchlist
- Alerts
- since-last-visit summaries

### Phase E — Administration

- Account
- Runs
- Errors/Events
- Doctor
- Database
- Settings

### Phase F — Polish

- PWA
- command palette
- saved views
- mobile polish
- accessibility
- performance audit
- empty/error states

Do not attempt all phases in one large unreviewable implementation.

## UX Master Rule

DealHunter must communicate information in this order:

DECISION
→ EXPLANATION
→ COMPARISON
→ TECHNICAL DATA

The main interface should tell the user what is worth buying and why.

Historical and technical information should remain available for deeper investigation without dominating everyday use.

## Future Scope — Not Immediate

Do not block the web implementation on:

- Android notifications
- brand inference
- inflation adjustment
- prediction
- basket optimization
- external multi-retailer expansion
- AI/LLM matching

These remain future work unless explicitly requested.


---

# Web Application & UX Architecture

## Strategic Direction

DealHunter's next major evolution is a local web application for shopping and price intelligence.

The web interface must NOT be treated as a graphical wrapper around SQLite or the CLI.

Its primary purpose is to help the user answer:

1. What is worth buying today?
2. Where is it cheapest right now?
3. Is the advertised deal actually good according to historical data?
4. How has the price changed over time?
5. What changed since the user's last visit?
6. Is DealHunter itself operating correctly?

The interface must preserve the existing principles:

- local-first
- privacy-first
- explainable
- conservative
- KISS
- offline-capable
- lightweight
- Termux/Android friendly
- no duplicated domain logic

## Primary Information Architecture

The UI is organized into four major functional areas:

### COMPRAR

Focused on discovering what is worth buying now.

Primary views:

- Inicio
- Oportunidades
- Supermercados
- Turbo
- Restaurantes
- Categorías

### INVESTIGAR

Focused on understanding products, prices and stores.

Primary views:

- Productos
- Tiendas
- Comparador
- Histórico

### SEGUIR

Focused on products and conditions the user wants to monitor.

Primary views:

- Watchlist
- Alertas

### ADMINISTRAR

Focused on DealHunter itself.

Primary views:

- Cuenta Rappi
- Actividad / Runs
- Errores / Eventos
- Doctor
- Base de datos
- Configuración

Do not flatten all pages into one large navigation menu if hierarchy provides a clearer experience.

## Contextual Views

The application must support contextual drill-down views for:

- Category
- Store
- Product

Navigation should naturally support flows such as:

Inicio
→ Oportunidad
→ Categoría
→ Producto
→ Comparar tiendas

and:

Supermercados
→ Tienda
→ Categoría
→ Producto
→ Histórico

Use breadcrumbs for deep navigation when useful.

## Home

Home should answer:

"What is worth buying today?"

Prioritize:

- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- meaningful price drops
- target prices reached
- back-in-stock events
- best current cross-store opportunities
- watched products
- useful category discovery

Administrative statistics should remain secondary.

Preferred information hierarchy:

DECISION
→ EXPLANATION
→ COMPARISON
→ TECHNICAL DATA

## Opportunities

Provide a dedicated opportunities view supporting:

- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- PRICE_DROP
- TARGET_PRICE
- BACK_IN_STOCK
- SUSPICIOUS_REFERENCE_PRICE

Useful filters include:

- vertical
- category
- store
- availability
- price
- deal status

Useful sorting includes:

- best opportunity
- lowest current price
- lowest unit price
- largest real price drop
- largest discount vs median
- newest historical low
- most recent

Do not invent opaque ranking systems when existing explainable metrics are sufficient.

## Vertical Views

Maintain distinct views for:

### Supermercados

Represents Market stores and products.

### Turbo

Uses shared components where appropriate but remains a distinct vertical.

Cross-store comparisons against Market products may be shown when safe matching exists.

### Restaurantes

Must use restaurant-appropriate UX rather than supermarket product UX.

Restaurant pages should be restaurant/menu oriented.

When `has_toppings` or modifiers exist and only base price is known, explicitly identify displayed prices as base prices.

Do not imply modifier-inclusive totals when they are unavailable.

## Categories

Categories should be a first-class exploration mechanism.

Use provider category metadata when available.

Do not invent a complex universal taxonomy during the first web implementation.

A future canonical category mapping may use:

provider_category
→ category_alias
→ canonical_category

but this is not required initially.

## Store Detail

A store view may include:

- current product count
- NEW_LOW
- REAL_DEAL
- GOOD_PRICE
- categories
- largest price drops
- products increasing in price
- current promotions
- products currently cheaper here than equivalent products in other stores

Do not claim that a store is universally cheaper based only on opportunity counts.

## Product Detail

Product Detail is a highest-priority experience.

It should expose, when available:

- current price
- previous price
- unit price
- availability
- deal status
- reason
- advertised promotion
- median 30d
- historical minimum
- historical maximum
- historical average
- price changes
- observation history
- cross-store comparison

Recommended sections/tabs:

- Resumen
- Histórico
- Comparar
- Observaciones

Historical charts should support useful ranges such as:

- 7D
- 30D
- 90D
- all

Useful reference lines may include:

- current price
- median 30d
- historical minimum

## Cross-Store Comparison

Always distinguish:

- best current store
- historical minimum
- best historical value

`best_store` means the store with the lowest CURRENT comparable price.

Never select today's best store because another store had a lower price in the past.

Show both absolute price and unit price when appropriate.

## Advertised Discount vs Historical Value

The UI must visibly preserve DealHunter's core rule:

The biggest advertised discount is not necessarily the best deal.

When `SUSPICIOUS_REFERENCE_PRICE` is present:

- treat it as a flag
- explain the historical inconsistency
- do not accuse a store of fraud
- do not automatically promote the product to REAL_DEAL

## Watchlist and Alerts

Visually group these under the SEGUIR area while keeping their behavior distinct.

Watchlist may display:

- current price
- target price
- distance to target
- best current store

Alerts may display:

- TARGET_PRICE
- NEW_LOW
- REAL_DEAL
- PRICE_DROP
- BACK_IN_STOCK

Support NEW/SEEN state.

Android system notifications are a future transport layer and must remain decoupled from alert detection logic.

## Account Diagnostics

Provide a read-only Cuenta Rappi diagnostics view.

It may expose only sanitized information such as:

- configured/not configured
- session valid/invalid
- region/market
- membership context
- promotion counts
- last check time

Never expose or persist:

- bearer tokens
- cookies
- personal names
- email
- phone number
- addresses
- payment data
- device identifiers
- sensitive account IDs

Do not provide a web form for persistently saving a Rappi bearer token.

Account network diagnostics must be explicit/opt-in.

Opening the account page must not silently trigger network requests.

## Runs / Activity

Represent execution history as structured activity rather than raw database rows.

Useful run information includes:

- execution type
- timestamp
- duration
- status
- request count
- products processed
- observations created
- partial-run reason
- related structured errors

Support SUCCESS, PARTIAL and FAILED views where applicable.

## Errors / Events

Prefer structured events over raw log dumps.

Useful fields:

- timestamp
- severity
- component
- error code
- run
- sanitized message

Existing structured error codes include:

- NETWORK_ERROR
- TIMEOUT
- HTTP_429
- CLOUDFLARE_LIMIT
- INVALID_RESPONSE
- PARSER_ERROR
- DB_LOCKED
- DB_CORRUPT
- CONFIG_ERROR
- PARTIAL_RUN
- REQUEST_BUDGET_REACHED

Never persist raw API responses merely to support the web event viewer.

Future event storage, if needed, must remain sanitized.

Useful historical views may include:

- errors over time
- HTTP 429 frequency
- timeouts
- partial runs
- errors by vertical

## Doctor

Expose local Doctor health information visually.

Examples:

- Catalog
- Turbo
- Restaurants
- Account
- Database
- SQLite integrity
- schema version
- overall health

Default page loading must use local checks.

Any network diagnostics must require an explicit user action.

## Database Administration

Safe initial actions:

- inspect DB statistics
- inspect schema version
- inspect integrity
- create backup

Avoid destructive database controls in the first web implementation.

Do not expose arbitrary SQL execution.

## Configuration

Separate GLOBAL CONFIGURATION from VIEW PREFERENCES.

Global configuration changes DealHunter behavior.

Possible sections:

- General
- Crawler
- Historical
- Price Intelligence
- Alerts
- Account
- Interface
- Database
- Advanced

Show effective value and configuration source where practical.

Configuration precedence remains:

CLI
> Profile
> Global config
> Internal defaults

Never allow secrets/tokens to be persisted through web configuration.

## View Preferences

View preferences affect presentation only.

Examples:

- filters
- sorting
- page size
- cards/table
- theme
- density

Pure UI preferences should normally use browser localStorage instead of SQLite.

Recommended preferences:

Theme:
- SYSTEM
- LIGHT
- DARK

Density:
- COMFORTABLE
- COMPACT

Product view:
- CARDS
- TABLE

## Search

Provide global search for:

- products
- stores
- restaurants
- categories

Search must be server-side and bounded.

Never load the entire product database into the browser.

A desktop command palette such as Ctrl+K is desirable but optional.

## Saved Views

Future saved views may store useful filter combinations such as:

- NEW_LOW beverages
- REAL_DEAL pharmacy
- cheapest unit-price products

Prefer localStorage initially unless server-side persistence becomes necessary.

## Since Last Visit

A future/useful dashboard feature should summarize meaningful changes since the user's last visit:

- new historical lows
- new real deals
- target prices reached
- price drops
- back-in-stock events

Browser-local last-visit state is preferred initially.

## Global System Status

Provide a compact global status indicator such as:

DealHunter OK

It may summarize:

- last update
- last run
- database health
- account context
- new alerts

Detailed administration remains under ADMINISTRAR.

## Recommended Web Stack

Preferred lightweight stack:

- Python
- Flask
- Jinja2
- HTMX
- Bootstrap 5
- Chart.js

Assets should work locally/offline.

Avoid introducing:

- React
- Vue
- Angular
- Node/npm build pipelines
- SPA complexity

unless a future requirement clearly justifies them.

## Web Architecture

Preferred architecture:

SQLite
→ existing DealHunter domain/services
→ thin web service layer
→ Flask routes
→ Jinja / HTMX
→ browser

The web layer MUST reuse existing logic for:

- normalization
- historical calculations
- Price Intelligence
- matching
- cross-store comparison
- watchlist
- alerts
- configuration

Never implement a separate web-only version of domain rules.

## API Strategy

Do not build a large REST platform unnecessarily.

Small local endpoints are acceptable where useful, for example:

- dashboard
- search
- product history
- compare
- alerts

Prefer server-rendered HTML and HTMX fragments when simpler.

## Performance

The product database already contains tens of thousands of products.

Requirements:

- server-side pagination
- bounded queries
- SQL filtering
- LIMIT
- avoid N+1 queries
- lazy-load expensive charts
- never load the entire product catalog into browser memory
- add indexes only when real measurements justify them

The UI should feel effectively instant during normal localhost navigation.

## Responsive UX

The application must be designed for both desktop and Android/mobile use.

Desktop may use a persistent sidebar.

Mobile should prefer a compact bottom navigation for high-frequency areas such as:

- Inicio
- Deals
- Buscar
- Seguir

Less frequent functions belong in a secondary menu.

Do not merely shrink the desktop UI.

## PWA Direction

The web application should remain compatible with future local PWA support.

Potential future additions:

- manifest
- app icon
- standalone display mode
- theme color

Do not cache sensitive/dynamic database content inappropriately.

## Security

The local web server must bind by default to:

127.0.0.1

Never expose DealHunter to the LAN by default.

Do not serve as static files:

- SQLite databases
- backups
- personal configuration
- tokens
- sensitive logs
- API dumps

Network exposure must require an explicit future configuration decision.

## Web Error UX

User-facing errors should be concise and useful.

Prefer:

"Could not read history.
Code: DB_LOCKED.
Your data has been preserved."

with optional technical details.

Do not show raw stack traces by default.

## Implementation Priority

Implement incrementally.

### Phase A — Foundation

- Flask
- layout/navigation
- responsive shell
- design system
- light/dark
- shared components
- search foundation

### Phase B — Shopping

- Home
- Opportunities
- Supermarkets
- Turbo
- Restaurants
- Categories

### Phase C — Investigation

- Product
- Store
- History
- Compare

### Phase D — Follow

- Watchlist
- Alerts
- since-last-visit summaries

### Phase E — Administration

- Account
- Runs
- Errors/Events
- Doctor
- Database
- Settings

### Phase F — Polish

- PWA
- command palette
- saved views
- mobile polish
- accessibility
- performance audit
- empty/error states

Do not attempt all phases in one large unreviewable implementation.

## UX Master Rule

DealHunter must communicate information in this order:

DECISION
→ EXPLANATION
→ COMPARISON
→ TECHNICAL DATA

The main interface should tell the user what is worth buying and why.

Historical and technical information should remain available for deeper investigation without dominating everyday use.

## Future Scope — Not Immediate

Do not block the web implementation on:

- Android notifications
- brand inference
- inflation adjustment
- prediction
- basket optimization
- external multi-retailer expansion
- AI/LLM matching

These remain future work unless explicitly requested.
