# DEALHUNTER_PHASE5A01_BASELINE_PROMOTION

> [!IMPORTANT]
> Historical phase snapshot. It records the evidence and constraints observed in
> that phase; it is not current operational guidance. Current RC truth is
> v3.2.0 / schema v16: Rappi and Uber acquisition are production-capable, while
> canonical matching remains shadow-only, automatic writes are OFF, human
> ground truth is insufficient and the statistical gate is `NOT_MET`.


## GIT
- **starting main**: cfa8393
- **audit branch**: 515d9c7
- **merge commit**: 4f27087
- **final main**: 4f27087
- **clean**: yes
- **pushed**: yes

## FIXES
- **P1 location**: Strict validation via 400 rejection in admin.py to avoid accidental crawls using fallback coordinates.
- **P2 empty stores**: Backend filters out `prod_count == 0` for `/stores` UI, while preserving `/stores/<id>` template rendering with explicit empty-states.
- **P3 price rendering**: Stripped trailing markdown tildes (~) from Jinja templates rendering original price.
- **unrelated changes**: None.

## REGRESSION TESTS
- **location**: Added `test_run_start_missing_location` and `test_run_start_valid_location`.
- **empty store**: Added `test_stores_index_hides_empty`, `test_stores_index_shows_all_with_flag`, `test_store_detail_empty_state`, `test_store_detail_full_state`.
- **price rendering**: Added `test_product_card_strike_through_formatting`.
- **filter smoke**: Passed manual validation over dynamic URL facet tracking.

## QUALITY
- **tests before**: 393
- **tests after**: 400
- **collected**: 400
- **passed**: 400
- **failed**: 0
- **CI run**: 32778166523
- **CI conclusion**: success

## UX BASELINE
- **critical routes**: 24/24 operational.
- **passing**: 24
- **P0**: 0
- **P1**: 0
- **P2**: 0
- **empty-store regressions**: 0
- **filters**: PASS
- **PUBLIC/PRO**: PASS
- **pagination**: PASS
- **search**: PASS

## QUICK_START
- **clean clone**: Validated against isolated temporary directory.
- **steps**: 18
- **passed**: 18
- **failed**: 0
- **human gates**: 4 (Shizuku, Session, Install, Start).
- **undocumented assumptions**: None found.

## DOCUMENTATION
- **README**: Updated version.
- **CHANGELOG**: Added `v3.0.1`.
- **AGENTS**: Version updated.
- **Quick Start**: Proven accurate.
- **Scheduler**: Functioning lock.
- **Alerts**: Tested.
- **Architecture**: Intact.
- **Mermaid**: Unchanged (Uber postponed).
- **Uber-only roadmap corrected**: Fixed Playbook to mandate regression validation against reference provider before adding a second one (discarding Sam's Club theory as the primary next goal).

## SECURITY
- **secrets**: PASS.
- **DB/backups**: PASS.
- **coordinates**: PASS.
- **result**: SAFE.

## RELEASE
- **version**: v3.0.1
- **commit**: 4f27087
- **tag**: v3.0.1
- **release**: https://github.com/yorologo/DealHunter/releases/tag/v3.0.1
- **schema**: 14
- **CI**: success

## BASELINE
- **frozen**: YES
- **reference document**: `docs/DEALHUNTER_V3_0_1_BASELINE.md`
- **regression contract**: ESTABLISHED

## DECISION
- **v3.0.1 successfully published**: YES
- **baseline UX trustworthy**: YES
- **Quick Start trustworthy**: YES
- **Rappi regression baseline frozen**: YES
- **blocker**: NONE
- **ready for Uber Eats architecture planning**: YES
