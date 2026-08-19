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

## Core Principles

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
