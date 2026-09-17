# Provider Integration Playbook

This playbook documents the formalized, step-by-step methodology for integrating new retail providers (e.g., Rappi, Uber Eats, Sam's Club) into DealHunter's local-first architecture. It encapsulates the lessons learned during the complex Phase 4 (Rappi Android Integration).

## 1. DISCOVER
- Broadly survey all possible network surfaces (Web, Mobile, Backend APIs).
- Maintain a "Thinking" approach: cast a wide net, log endpoints, and do not immediately build schemas for everything.
- Identify the highest-density catalog endpoints.

## 2. INVENTORY SURFACES
- List and categorize the discovered endpoints.
- E.g., `A5` (Stores/Verticals), `B1` (Turbo Catalog), `D1` (Faceted Navigation).

## 3. CLASSIFY & VALIDATE CONTRACT
- Deconstruct the JSON payload.
- Prove what the provider *actually* sends versus what the keys *imply*.
- Example: Do not assume `vertical_sub_group` is authoritative until proven across multiple verticals.
- Validate pagination contracts (Cursor-based, Offset-based, limitations).

## 4. MEASURE & SHADOW TEST
- Run non-destructive, silent scripts that fetch and parse the surface alongside existing production data.
- Measure coverage (e.g., A5 returned 218 stores, missing 5 legacy ones).
- Classify the misses (Stale, Unuspported Vertical, Parser Logic).

## 5. INTEGRATE & RECONCILE BY SCOPE
- Build the parsers.
- **Scope-Safe Reconciliation**: Never mark a store or product as `STALE`/`UNAVAILABLE` if the current surface didn't genuinely attempt to fetch that specific scope. If A5 doesn't cover "Liquor", do not mark Liquor stores as dead.
- **Fail-Open**: When in doubt, leave data untouched rather than aggressively archiving it.

## 6. MODEL CONDITIONAL PRICING
- Extract commercial models (Public vs Pro, NxM, Progressive).
- **NULL != False**: An un-evaluated state (e.g., missing Pro membership token) must be explicitly recorded as `NULL`, never `0` (False). `0` strictly means "Evaluated and proven to have no Pro offer".
- **Conservative Conclusions**: Never infer discounts or synthesize data. Let the database reflect reality.

## 7. MIGRATE & QUERY
- Use strict, versioned SQLite migrations.
- Build the Query Layer adopting the standard boolean rule: **OR within a dimension, AND across dimensions**.
- Favor `EXISTS` subqueries over Cartesian `JOIN`s for M:N relationships (like Collections and Store Facets).
- **Current vs Historical**: Use temporal window functions (`ROW_NUMBER() OVER (...)`) to deduplicate observations cleanly without relying on brittle `UPDATE` triggers.

## 8. UI INTEGRATION
- Push the semantic faceted logic all the way to the frontend UI.
- Use query strings (`?vertical=X&category=Y`) to preserve application state.
- **Dynamic Categories**: Only present options relevant to the *current* filter scope. Do not list categories for Store B when Store A is selected.

## 9. PRODUCTION VALIDATION
- Benchmark queries on a full-sized local DB (~100k+ rows) on Termux (Android).
- Run `EXPLAIN QUERY PLAN` before creating any indexes.
- Only introduce indexes when the benchmark proves a significant win (e.g., temporal index `idx_obs_history`).

## 10. DATABASE OPTIMIZATION
- **Index only after benchmark + EXPLAIN**.
- Validate read gain vs write cost. In Schema V13, introducing `idx_obs_history` eliminated the temporary B-Tree sort during `ROW_NUMBER()` deduplication, reducing Facet computation from ~1400ms to ~800ms while incurring <1ms penalty on a 1000-row batch insert.

## 11. IMMUTABLE SNAPSHOTS
- Always create an immutable PRE and POST snapshot (using SQLite backup or file copies) before and after large crawler/schema phases to ensure you can calculate strict delta metrics and detect any silent commercial logic corruptions. (Learned during Phase 4E).

## Taxonomy & Semantic Rules (Phase 4F Lessons)
1. **UNKNOWN is preferable to invented taxonomy**: Do not guess `CATEGORY` vs `COLLECTION` based on strings that "sound" like categories. Keep them as `UNKNOWN` until proven.
2. **Characterize before mapping**: Always extract distributions (top names, paths, stores) of `UNKNOWN` data before writing any rules.
3. **Evidence Hierarchy**: Exact structural IDs > Exact structural paths > Exact normalized labels within identical store contexts > Heuristics.
4. **Secondary Oracle**: Use a secondary, data-rich surface (like the Web SSR `__NEXT_DATA__`) to validate and extract structural IDs (e.g. `aisle_type=generic` vs `aisle_type=seasonal`) when the Primary surface (Android API) omits them.
5. **Negative Controls**: Validate your classification rules against nodes known to cause collisions (e.g. "Regreso a Clases" should be COLLECTION, not CATEGORY).
6. **Precision > Coverage**: A 28% reduction in noise with 100% precision is vastly superior to a 90% reduction with false positives.
7. **Reuse Network Requests**: Whenever possible, piggyback semantic metadata extraction onto the existing catalog fetch (e.g., snagging `aisle_type` during the SSR crawl) to keep extra network requests at exactly 0.
8. **Provenance**: Always record exactly *why* a semantic classification was applied (e.g. `web_exact_category_id`).

9. **Never assume provider IDs are globally semantic until cross-context invariance is demonstrated.** An ID like `265` might mean 'Lácteos' in Turbo, but could mean something else entirely in a Restaurant menu. Always scope fallback dictionaries to the `parent_type` unless global invariance is strictly proven.

## Longitudinal Validation & Mid-Flight Bugs

Durante una fase longitudinal, si aparece un bug:

1. **PAUSE** execution immediately.
2. **Preserve** pre-fix evidence (do not overwrite the DB or delete old runs).
3. **Fix** the bug and write tests to reproduce it.
4. **Restart** a comparable baseline to gather new evidence.
5. **Do not merge** pre-fix and post-fix metrics blindly when evaluating reliability.

This ensures temporal metrics (like out-of-stock transitions or false positives) are not polluted by the bug's side-effects.

## Production Cutover & Live Alerts (Phase 4I Lessons)
When automating alerts for a new provider:
- **Event != Delivery**: Always log state transitions internally before wiring up user-facing delivery.
- **Historical Cutover Boundary**: Past events must be explicitly suppressed (`delivery_status = 'historical'`) before enabling live schedules to prevent retroactive spam floods.
- **High-Signal Watch First**: Start with highly restrictive, conservative rules (e.g., `NEW_PRODUCT_WITH_DEAL >= 50%`) for the first canary phase.
- **Noisy Events**: Record noisy events (like 10% price drops or OOS/BIS oscillations) silently. Do not deliver them until they prove reliable.
- **Idempotency Before Automation**: Before configuring a cron, replay the exact same run twice and assert `0` new duplicate alerts are generated.
- **Scheduler Singleton Protection**: Enforce a strict OS-level lock (e.g. `flock`) so two crawlers never write to the DB simultaneously.
- **Delivery Failure Isolation**: If the notification provider (e.g., Termux:API) crashes, the core crawler must gracefully continue and the database should track the failed delivery attempt.

## Final Stage: Release Promotion Pipeline
1. **RELEASE CANDIDATE (RC)**: Branch integration creates RC1.
2. **OPERATIONAL SOAK**: The precise RC artifact is monitored in a live scheduled environment to guarantee no alert floods or memory leaks.
3. **STABLE PROMOTION**: Only if soak passes, a clean metadata-only release commit promotes the software to stable.

*Key Lesson:* Never develop new features on top of an unproven RC. Always preserve RC tags immutably, and revalidate the final stable commit before tagging.

## Multiprovider Expansion Rules

- Freeze and certify the existing provider UX baseline before introducing a second provider.
- Every multiprovider phase must prove no regression against the reference provider.
