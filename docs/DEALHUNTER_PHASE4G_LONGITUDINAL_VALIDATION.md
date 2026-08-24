# DealHunter Phase 4G: Longitudinal Validation

## Overview
Phase 4G proves DealHunter's stability over multiple sequential crawls (simulating chronological runs). It establishes the rules for temporal transitions necessary for the upcoming Alerts Engine (Phase 4H).

## Temporal Semantics Discovered
1. **Disappearances**: A product missing from a `__NEXT_DATA__` SSR payload during a successful store sync is truly unavailable. One single run of absence is sufficient to safely declare `UNAVAILABLE` or trigger an `OUT_OF_STOCK` alert.
2. **Taxonomy Regression Prevention**: A structural regression was caught where nodes lacking direct `aisle_type` downgraded offline-backfilled categories to `UNKNOWN`. By extracting `aisle_type` from the root SSR `corridors` mapping, the engine now autonomously assigns `CATEGORY` (generic) and `COLLECTION` (seasonal) dynamically without relying on the historical crosswalk.
3. **Price Drops**: Extremely common. An alert engine must require a significant threshold (e.g., >10% or crossing a specific median).
4. **New Deals**: `discount_effective >= 50%` transitions are rare and highly reliable. They require zero additional confirmation runs.

## Failure Behavior
- **Partial Crawls**: If a crawl aborts (e.g. `timeout` or `--max-runtime`), the engine safely preserves previously crawled stores. Uncrawled stores are *not* falsely marked as `STALE`. Products in uncrawled stores are *not* marked as `UNAVAILABLE`. This strict separation is vital for alert reliability.
- **Data Integrity**: Integrity checks and foreign keys remain flawless (`ok` and `0` respectively) throughout repeated heavy mutations.
