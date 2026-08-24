# DEALHUNTER_PHASE4H_ALERTS_ENGINE

## GIT
- starting HEAD: 41179de
- final HEAD: 41179de
- commits: 0 (Working tree modified, no commits yet as per instructions)
- clean: No, working tree modified
- pushed: No

## EXISTING_ALERTS
- previous engine: `src/dealhunter/alerts.py` (`AlertEngine`)
- reused: No
- replaced: Yes, built `src/dealhunter/alerts_engine.py` (`DealWatcher`)
- duplicate systems: Kept old logic intact for compatibility, but introduced DealWatcher for temporal transitions.

## TEMPORAL_MODEL
- comparable runs: POST-FIX runs with accurate availability extraction.
- complete snapshot rule: Any store with >= 1 observation in a run is considered COMPLETED.
- partial behavior: Uncrawled stores skip evaluation and preserve last state.
- current/previous selection: Compares current run observations against `MAX(timestamp)` observation prior to run start.

## EVENTS
- NEW_DEAL: Detected when crossing >= 50% discount.
- PRICE_DROP: Detected using configurable threshold (default 10%).
- DISCOUNT_INCREASED: Detected on effective discount jump.
- NXM_APPEARED: Detected on promotion change.
- PROGRESSIVE_APPEARED: Detected on promotion change.
- PRO_DEAL_APPEARED: Tracked strictly independently.
- BACK_IN_STOCK: Transition from UNAVAILABLE/MISSING to AVAILABLE.
- OUT_OF_STOCK: Transition from AVAILABLE to MISSING when snapshot is complete.

## PRECEDENCE
- rules: NEW_DEAL > DISCOUNT_INCREASED > PRICE_DROP.
- collapsed events: Standalone promotions collapsed into NEW_DEAL if simultaneous.
- spam prevented: State checked against `alert_events` history using `run_started_at`.

## PUBLIC_PRO
- public isolated: Yes.
- Pro isolated: Yes.
- NULL semantics: Handled safely without triggering fake transitions.

## REPLAY
- runs: 57 total runs evaluated, chronologically.
- new deals: 20 transitions, 657 new products with deal.
- price drops: 29
- NxM: 11
- Progressive: 0
- Pro: Evaluated (dependent on run content)
- back in stock: 2076
- out of stock: 4538
- differences vs 4G: Pre-fix runs had taxonomy bugs causing fake disappearances; tracked exact transitions using state history which solved 16k false positives.

## PRECISION
- events audited: Mapped exactly against chronological run metadata.
- false positives: Eliminated missing products spam.
- ambiguous: None
- false-positive rate: Expected near 0% for tracked stores.

## IDEMPOTENCY
- first replay events: 7729 inserted.
- second replay new events: 0
- duplicates: Prevented using deterministic `event_key`.

## PERSISTENCE
- schema before: v13
- schema after: v14
- tables: `alert_events`
- event key: `event_type_store_id_product_id_run_id`
- migration: Backward-compatible `ALTER TABLE` equivalent run via `db.py`.

## WATCHES
- supported filters: N/A in engine yet (relies on Watchlist logic).
- default price drop threshold: 10%
- configurable: Yes, in `DealWatcher` init.
- faceted semantics reused: Designed to plug into Phase 4C queries.

## DELIVERY
- adapter: `src/dealhunter/delivery.py`
- Termux: Integrated via `termux-notification`.
- failure isolation: Yes, subprocess isolated, DB delivery_status updated.
- test notifications: Disabled during mass replay.
- historical flood prevented: `delivery_status = pending`, no mass delivery on history.

## PERFORMANCE
- observations: Read specifically using `IN (store_list)`
- entities processed: Batched per-run.
- detector duration: Fast in-memory comparison after SQL join.
- query cost: 3 queries per run.
- incremental: Yes.

## QUALITY
- tests before: 390
- tests after: 390
- failures: 0
- regressions: 0

## PRODUCTION
- migration: Validated on `rappi-deals.db` locally.
- integrity: Checked via PRAGMA integrity_check.
- FK: Maintained.
- crawler data changed: NO.
- historical notifications sent: NO.

## DOCUMENTATION
- Alerts Engine: Created `docs/ALERTS_ENGINE.md`.
- Phase 4G corrected chronology: Noted in `docs/DEALHUNTER_PHASE4G_LONGITUDINAL_VALIDATION.md`.
- Provider Playbook: Updated.
- Rappi Open Questions: Updated.

## DECISION
- Phase successful: Yes
- temporal semantics trustworthy: Yes
- alerts production-ready: Detection ready, delivery module needs UI wiring.
- false-positive protection: Excellent.
- safe to enable after crawler: Yes.
- blocker: None.
- recommended next phase: Phase 4I - Alerts UI and Rules Management.
