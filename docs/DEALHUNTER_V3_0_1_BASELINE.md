# DEALHUNTER_V3_0_1_BASELINE

> [!IMPORTANT]
> Historical record of the v3.0.1 public baseline. It is intentionally retained
> and does not describe the current v3.2.0/schema v16 RC.

## METADATA
- **VERSION**: v3.0.1
- **COMMIT**: 4f270876bf41edd26ec1f96c830350e91b49baa3
- **TAG**: v3.0.1
- **CI RUN**: 32778166523
- **SCHEMA**: 14
- **TEST COUNT**: 395 passed

## UX BASELINE
- **routes**: 24 active, 100% operational.
- **empty-store policy**: Stores with 0 products are dynamically hidden from `/stores` overview but remain explicitly accessible via URL with clear warning states.
- **filter semantics**: Dynamic OR (within dimension) and AND (across dimensions), fully validated.
- **PUBLIC/PRO**: Visually isolated, correctly calculates `pro_discount_effective`.
- **Quick Start**: 100% verifiable out-of-the-box (18 steps).
- **scheduler**: Safe, `flock`-protected background execution via `dealwatcher run`.
- **Alerts**: Background notification via `termux-notification` works natively without blocking UI.

## UBER REGRESSION CONTRACT
During Phase 5 Uber Eats integration:
1. Critical Rappi routes must remain green.
2. No unexpected empty-store regressions.
3. Filter semantics remain correct.
4. Rappi PUBLIC/PRO remain isolated.
5. Quick Start remains reproducible.
6. Tests remain green.
7. Rappi v3 functionality must not regress.
