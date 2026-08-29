# PHASE 5D.0 — SCHEMA-TEST DECOUPLING

> [!IMPORTANT]
> Historical phase snapshot. It records the evidence and constraints observed in
> that phase; it is not current operational guidance. Current RC truth is
> v3.2.0 / schema v16: Rappi and Uber acquisition are production-capable, while
> canonical matching remains shadow-only, automatic writes are OFF, human
> ground truth is insufficient and the statistical gate is `NOT_MET`.


## STATUS
COMPLETED (SCHEMA_TEST_DECOUPLING_CERTIFIED)

## BASE HEAD
1693035 (origin/feature/uber-eats-shadow-adapter)

## BRANCH
refactor/schema-test-decoupling-v14

## TEST BASELINE
409 passed in 46.16s

## TEST FINAL
409 passed in 47.13s

## COUPLING INVENTORY
- **Manual current DDL**: `test_zone_inventory.py`, `test_scope_reconciliation.py`, `test_faceted_schema.py`, `test_semantic_persistence.py`
- **Positional inserts**: `test_migration.py`, `test_semantic_persistence.py` (legacy schema testing)
- **Legacy DDL**: Preserved in migration tests as isolated fixtures.
- **Negative fixtures**: Preserved.

## REFACTOR
- **Canonical DB Factory**: Centralized test database initialization into `current_schema_db` fixture in `tests/conftest.py`.
- **Semantic insert helpers**: Created in `tests/helpers/db.py` to decouple inserts from physical column order (e.g. `insert_store`, `insert_product`, `insert_run`).
- **Files migrated**: `test_zone_inventory.py`, `test_scope_reconciliation.py`, `test_web_filters.py`, `test_faceted_query.py`.
- **Exceptions**: Migration tests in `test_migration.py`, `test_semantic_persistence.py`, and `test_faceted_schema.py` where manual legacy DDL is required to test migrations.

## GRADUATION TEST
- **Harmless schema perturbation**: Added `__test_future_column TEXT DEFAULT NULL` to the `products` table in `dealhunter/db.py`.
- **Previously affected tests**: All canonical schema tests.
- **Structural failures**: 0. The positional layout failures (e.g., "5 values for 4 columns") are eliminated.
- **Semantic failures**: 0.
- **Result**: SUCCESS. The test suite is immune to non-breaking physical schema layout changes.

## PERFORMANCE
- **Before**: 46.16s
- **After**: 47.13s
- **Impact**: Minimal, standard variance.

## REGRESSIONS
- **Rappi**: PASS
- **Uber**: PASS
- **Web**: PASS
- **Query**: PASS
- **Alerts**: PASS
- **Scheduler**: PASS

## NEXT
- **v15 architecture/design gate**: Move to Phase 5D.1.

## RECOMMENDED V15 MODEL
Based on the decoupling, a hybrid/composite model `UNIQUE(provider, product_id)` or `composite provider-aware external keys` is the safest evolutionary path. The test infrastructure can now safely support structural schema evolution.
