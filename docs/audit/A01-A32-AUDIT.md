# A01–A32 canonical audit backlog

Authority for the current post-`v3.3.1` work on `develop`. These identifiers and definitions are stable for this audit. Historical ledgers use different IDs and are preserved only under `docs/audit/`.

## Wave 1 — Correctness / Security / Truth

- **A01 — Merchant/location operativo:** reviewed `Provider Listing → Merchant → Location`; ambiguity stays `UNRESOLVED`; raw `(provider, store_id)` is preserved; no name-based automatic merge.
- **A02 — Browse taxonomy operativa:** reviewed `provider raw taxonomy/path → browse_node` using `product_memberships`, `browse_nodes`, `browse_mappings`; missing evidence stays `UNCLASSIFIED`; no display-name inference.
- **A03 — Ordenamientos falsos del catálogo:** `savings`/`recent` must be authoritative and OFFSET/keyset equivalent; unsupported `opportunity` must not be advertised.
- **A04 — Recency real en Deals:** deal recency comes from the real latest observation/event timestamp (`latest_observed_at`), never wall-clock substitution.
- **A05 — Latest restaurant correctness:** latest per `(provider, store_id, product_id)` is `ORDER BY timestamp DESC, id DESC`; restaurant `last_obs` reflects the real latest member observation.
- **A06 — SecretStore filesystem fail-closed:** private atomic salt/ciphertext writes; partial failure preserves prior secret; NOT_CONFIGURED, CORRUPTED and storage I/O remain distinct.
- **A07 — Validación Web Admin:** provider/membership/status/comparison/settings reuse canonical contracts; invalid inputs do not persist; unknown booleans are errors; CLI/Web semantics align.
- **A08 — Open redirect:** mutable Web redirects accept only internal/same-origin targets; external/scheme-relative destinations are rejected or safely replaced.
- **A09 — Ledger confiable:** historical ID sets remain historical; A01–A32 are the immutable current audit identifiers.
- **A10 — Documentación canónica:** current README/AGENTS/architecture/roadmap/security/current docs reflect real version, schema, capabilities, releases and Web/module status; historical documents stay historical.

## Wave 2 — Performance / Architecture / Product completeness

- **A11 — Restaurant N+1:** restaurant listing metrics use one reusable aggregated/latest-observation query rather than per-store count queries.
- **A12 — Representative performance:** benchmark `analyze_history`, Home, Deals and Best; optimize only measured hot paths, preferring bounded SQL to premature materialization.
- **A13 — SQLite connection discipline:** progressively reuse KISS read/write helpers/context managers; read-only is genuinely read-only where practical.
- **A14 — Error truth:** DB/storage errors must not be rendered as false “no data”; correct only authority-destroying broad catches.
- **A15 — Visible IA:** progressively present Descubrir / Explorar / Buscar / Seguir / Sistema and `Commerce Type → Merchant → Branch → Catalog`, reusing current routes/services.
- **A16 — Filter UX:** desktop sidebar/drawer, mobile `Filtros (N)` drawer/fullscreen, active chips, and coherent branch scope ALL/INCLUDE/EXCLUDE without contradictory controls.
- **A17 — Keyset UX:** use existing cursor pagination for HTMX `Cargar más` append; retain `page=N` for compatibility/deep links.
- **A18 — Presentation translations:** translate technical enums only at presentation; internal semantics remain unchanged.
- **A19 — Home focus:** Home primarily answers “¿Qué vale la pena comprar?”; technical metrics move to Sistema/Admin; exploration reflects real commerce types.
- **A20 — Local search coverage:** current local search also finds Merchant, Branch/Location and Browse Category, not just products.
- **A21 — Alerts Web:** `/alerts` is a real read-only view over the existing AlertEngine; no second alert engine.
- **A22 — Modern authority:** new views prefer commerce_type/catalog_domain/merchant/location/browse taxonomy while legacy vertical/raw category/raw store compatibility remains.
- **A23 — Catalog Sync HTTP reuse:** audit duplicate HTTP behavior and reuse `AuthenticatedHttpClient` for equivalent auth/timeout/error/header contracts when demonstrated.
- **A24 — Retention policy:** KISS rotation/cleanup for logs and temporary diagnostics; commercial observation history follows explicit retention and is not deleted merely to save space.
- **A25 — CI/runtime install:** retain Python 3.11, add a modern Termux-compatible runtime when viable (prefer 3.14), and smoke `pip install .` plus installed import/execution without relying only on `PYTHONPATH=src`.
- **A26 — GitHub protection:** minimal ruleset for main/develop to prevent accidental force/delete and require green CI for promotion where compatible, without excessive bureaucracy.
- **A27 — Dependency bounds:** add tested KISS dependency constraints/bounds without a new lock-manager; preserve Android native-cryptography behavior.

## Wave 3 — Hardening / Deferred

- **A28 — Tailwind:** do not migrate now; reconsider only if Bootstrap is demonstrated to block the required IA/componentization.
- **A29 — Deal Score version:** explicit algorithm version plus regression corpus/fixtures; no ML.
- **A30 — Output contracts:** JSON/CSV contract tests only where a real external-consumer contract exists; version only public interfaces that actually behave as contracts.
- **A31 — Third-party inventory:** document vendored Bootstrap, HTMX and Chart.js versions/origins/licenses/hashes where reasonable.
- **A32 — SECURITY.md:** accurately state that authorized sessions may be imported/persisted locally and encrypted; remove any blanket claim that DealHunter handles no authentication.

## Global invariants

SQLite stays authoritative; no cloud or automatic product canonicalization is introduced. Merchant identity, location identity, product canonical identity and browse classification remain separate authorities. Product canonical matching remains SHADOW / EXPERIMENTAL with automatic membership writes OFF.

## Closure status

All A01–A32 items are closed on `develop` as of the post-v3.3.1 audit cycle.
Closure does **not** imply a release/tag; runtime version remains 3.3.1 until a
separate release decision is made. Deferred/negative decisions are explicit,
not silently treated as implementation.

| IDs | Status | Closure evidence |
|---|---|---|
| A01–A10 | CLOSED | Explicit merchant/location + browse mapping, authoritative sorts/recency, fail-closed SecretStore, Admin validation/redirects, current-doc cleanup. |
| A11–A22 | CLOSED | Aggregated/query-layer performance work, connection/error truth, visible IA/filter/keyset UX, translations/Home/search/alerts and modern commerce authority. |
| A23 | CLOSED | Catalog Sync equivalent authenticated HTTP behavior reuses `AuthenticatedHttpClient`; focused regressions cover optional auth. |
| A24 | CLOSED | `maintenance run` rotates only managed runtime logs/diagnostics; SQLite/commercial observation history is preserved. |
| A25 | CLOSED | CI installs the real package on Python 3.11 + 3.14, runs `pip check`, package-data/CLI smoke and full pytest without `PYTHONPATH`. |
| A26 | CLOSED (REMOTE) | Active GitHub rulesets: `develop` prevents delete/force-push; `main` also requires `Python 3.11` + `Python 3.14` checks. No mandatory PR/review bureaucracy added. |
| A27 | CLOSED | Explicit major-version dependency bounds; Android keeps native `python-cryptography` behavior. |
| A28 | CLOSED — NO MIGRATION | Bootstrap 5 + HTMX satisfied A15–A17; no demonstrated blocker justifies Tailwind churn. |
| A29 | CLOSED | `deal-score-v1` constant/result field + `tests/corpus/deal_score_v1.json`; deterministic regression gate; no ML. |
| A30 | CLOSED — BOUNDED | Public `deals --format json|csv` format contracts are tested/documented; business fields remain release-versioned, no artificial secondary schema version. |
| A31 | CLOSED | `docs/third-party-assets.md` records Bootstrap/HTMX/Chart.js versions, upstreams, licenses and exact SHA-256; tests pin hashes. |
| A32 | CLOSED | `SECURITY.md` and account diagnostics document ephemeral + opt-in Fernet SecretStore persistence and explicitly reject weak fallbacks/secrets in DB/config/logs. |

A28/A30 are intentionally minimal KISS decisions: they avoid adding a new CSS
stack or independent output-versioning system without demonstrated need.
