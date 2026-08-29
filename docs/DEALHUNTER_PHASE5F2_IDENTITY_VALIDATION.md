# Phase 5F.2 Identity Validation

## Human vs Model Labels
For this phase, a blind review of the 600-pair review corpus was conducted using an independent AI model, rather than relying strictly on human ground truth. This ensures separation from the heuristic rules, but these labels MUST NOT be considered `human ground truth`.

## Blind Review
The model evaluating the pairs had no access to the shadow matcher's decisions, confidences, or internal rationales. It produced independent labels (`EXACT_PRODUCT`, `PRODUCT_FAMILY`, `SIMILAR_PRODUCT`, `NO_MATCH`, `AMBIGUOUS`).

## Seed Gold
The 30-pair gold sample provided was evaluated. (Note: the current file only contained 4 pairs).
No `AUTO_CONFIRMED` false positives occurred.

## Calibration vs Holdout
To refine the heuristics moving forward without overfitting, future calibration must explicitly split the candidate pairs into a 70/30 (Calibration/Holdout) group to prevent data leakage and ensure metrics apply to unseen pairs.

## Leakage Controls
Duplicate pairs and highly repetitive product representations from the same brand across tests represent a leakage risk.

## Metrics
### Model-Assisted Metrics (600 pairs)
- EXACT_PRODUCT Auto Confirmed: 35
- PRODUCT_FAMILY Auto Confirmed: 14 (Disagreement)
- SIMILAR_PRODUCT Auto Confirmed: 8 (Disagreement)
The heuristic model over-indexes `AUTO_CONFIRMED` on non-exact products, meaning calibration is required.

## Exact Production Gate
- Audited AUTO_CONFIRMED target: 600
- Statistical Production Gate: NOT_MET
- 0 false positive requirement was NOT met due to 22 non-exact pairs classified as AUTO_CONFIRMED.

## Why Schema v16 Remains Deferred
Because the matcher requires calibration and the production gate was NOT MET, it is unsafe to roll out the Canonicalization database (schema v16) right now. Doing so would write faulty identity associations into the database. Schema v15 will remain intact.

## Performance
Candidate generation is currently O(N²) global over all products in the database. When tested on the main catalog, the script timed out. It needs to be bounded (e.g., grouped by brand and category before comparing) before it is production ready.
