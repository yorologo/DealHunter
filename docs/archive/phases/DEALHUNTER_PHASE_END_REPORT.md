# DealHunter Phase 5F-5I Status & Validation Report

Current development target: v3.2.0 (unreleased RC), schema v16. Runtime
authorities are `dealhunter.metadata.VERSION` and
`dealhunter.db.CURRENT_SCHEMA_VERSION`.

## Technical RC Status
- TECHNICAL_RC_READY: YES (certified by strict validation gates)
- AUTO_CANONICALIZATION_PRODUCTION_READY: NO
- RELEASE_CANDIDATE_READY: YES (with canonicalization safely gated off)
- HUMAN_BLOCKER: Ground truth evaluation is insufficient for automatic writes.

## Phase Classification
- 5F.2A (Gold Corpus): BLOCKED (Data missing, explicitly prevented)
- 5F.2B (Model Review): MODEL-ASSISTED ONLY (600 pairs; not human ground truth)
- 5F.3 (Shadow Matcher Calibration): EXPERIMENTAL (Exact Evidence Gate tuned strictly)
- 5F.4 (Production Identity Gate): STATISTICAL_GATE NOT_MET
- 5G (Schema v16): INFRASTRUCTURE IMPLEMENTED (no automatic canonical write path)
- 5H (Multi-provider Pricing): IMPLEMENTED (deal scoring isolated from canonical identity)
- 5I (Web/CLI): MOCKUP/EXPERIMENTAL (canonical_detail.html created as shadow layout)

## Identity Verification Truthfulness
- Rappi acquisition: production
- Uber acquisition: production, phone-only Termux Chromium headless
- Provider/membership configuration: production
- Identity matcher: shadow/experimental
- Gold ground truth: expected 30, available 0, blocked
- Model-reviewed corpus: 600
- Human-reviewed corpus: 0
- Auto candidates: experimental
- Statistical identity gate: NOT_MET
- Schema v16: implemented infrastructure
- Automatic canonical membership writes: no path implemented
- Canonical production comparison: NOT ENABLED

## Reproducible Candidate Benchmark

Command, executed four times with stable counts (including the final truth-gate
rerun):

```bash
PYTHONHASHSEED=0 PYTHONPATH=src \
  python scripts/benchmark_identity_candidates.py rappi-deals.db
```

Dataset and pair counts:

- eligible left (Rappi): 33,435
- eligible right (Uber Eats): 6,502
- theoretical cross product: 217,394,370
- screened after per-left-product cap: 1,147,815
- generated candidate pairs: 470,065
- candidate reduction: 99.7838% (not 99.9%)
- screened reduction before evidence filtering: 99.4720%
- generated per left product: average 14.0591, P95 65, max 100
- screened per left product: average 34.3297, P95 100, max 100
- clusters over cap: 4,541
- entries dropped by cap: 520,560

Observed runtime across the four fresh processes:

- actual `generate_candidates`: 6.050–6.691 s
- instrumented full pass: 5.717–5.966 s
- processing per left product: average 0.1457–0.1511 ms, P95 0.4812–0.5105 ms, max 3.556–12.110 ms
- actual peak RSS: 178.7–178.9 MiB

These are candidate-generation measurements, not identity precision metrics.
They provide no evidence of 100% precision or zero human false positives.
