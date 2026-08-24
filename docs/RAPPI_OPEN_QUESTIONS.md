# Rappi Open Questions & Triage

## DEFERRED
- **Advanced Watch UI**: Postponed for Web Application Phase 5.
- **Event Digest / Bundling**: If Termux alerts exceed 20/day consistently, implement summary digests rather than immediate pings.
- **Turbo Deep Inventory Reconciliation**: Complex catalog mismatches between Market and Turbo.
- **Live Pro Validation**: Need more test accounts with active Pro subscriptions to validate dynamic `has_pro_offer = 1` assertions.
- **B1 / D1 Endpoints**: Too volatile; deferred indefinitely unless A5 is deprecated.

## NON-BLOCKING
- **Residual UNKNOWN memberships**: 5,000+ items remain `UNKNOWN`. Harmless to operations, purely cosmetic for discovery filters.
- **Liquor Scope Completeness**: Some alcohol vendors hide behind age-gate dynamic redirects on Web, causing slight observation drops.

## RESOLVED
- **Alerts Idempotency**: Fixed via `DealWatcher` tuple matching.
- **Scheduler Concurrency**: Fixed via `flock`.
- **Promotion Contamination**: Fixed by explicitly modeling `discount_effective` vs `pro_discount_effective`.
- **Taxonomy M:N Bug**: Fixed via `product_memberships`.
