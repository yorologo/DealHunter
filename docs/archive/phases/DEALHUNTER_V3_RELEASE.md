# DealHunter v3.0.0 Release Documentation

> [!IMPORTANT]
> Historical v3.0.0 release-cycle snapshot. Pending markers and schema claims
> below belong to that cycle, not the current v3.2.0/schema v16 RC.

## PATH TO STABLE
- **RC1**: b1afaa94c8ccda57b600b2c00ca8a4103b2fc2a6 (CI: 32769390355)
- **RC2**: 05397540ca931194d0925f9963c638b78ace41b2 (CI: 32771799961)
- **STABLE**: <PENDING> (CI: <PENDING>)

## HIGHLIGHTS
v3.0.0 is the first stable release of the new integrated Rappi Phase 4 pipeline.

- **A5 Discovery**: Stable fallback mechanisms and scope-safe reconciliation.
- **Faceted Taxonomy**: M:N memberships, `CATEGORY`/`COLLECTION`/`UNKNOWN` semantic logic, dynamic `aisle_type`.
- **Alert Engine**: Fully temporal, idempotent alert events, integrated canary Watch.
- **Commercial Intelligence**: NxM promotions, PRO pricing split.
- **Automated Scheduler**: Daily background `crond` pipeline via Termux.

## RC2 SOAK VERDICT
The DealHunter v3.0.0-rc2 baseline was successfully verified across simulated daily scheduled runs representing operational timeframes (07:00, 10:00, 13:00, 19:00).
- Lock/Concurrency validation: PASS (`flock` prevents multiple instances)
- Notifications: PASS (Termux deliveries successful)
- DB Integrity: OK (Schema 14 preserved, 0 FK errors)

*DealHunter has successfully reached Phase 4 completion.*
