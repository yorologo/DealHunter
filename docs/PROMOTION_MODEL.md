# DealHunter Commercial Promotion Model

DealHunter evaluates all promotional signals provided by the provider and normalizes them into an objective, explainable mathematical structure.

## Promotion Types

- **Direct**: Traditional percentage or fixed monetary discounts. Evaluated reliably by comparing `price` vs `real_price`.
- **NxM**: Bundle conditions where `units_condition` units are paid and `promotion_value` units are received (e.g. 3x2).
- **Progressive**: Unit-dependent scalable discounts (e.g., "-24% on the 2nd unit"). DealHunter calculates the *effective bundle discount* of acquiring the minimum required units.
- **Progressive Unknown**: If a complex conditional structure cannot be confidently reduced to an effective unit cost, it is flagged but its percentage is left `NULL` to prevent false positives.

## Pro & Prime Offers

DealHunter preserves the public non-member price while distinctly extracting `pro_exclusive` status and `pro_price`.
A Pro-exclusive deal >= 50% discount will NOT replace the standard public product classification, but is logged with `is_pro_exclusive = 1` in the database to allow conditional filtering for Pro members.

## Precedence and Deduplication

Multiple promotions can exist on the same product (e.g. a 3x2 deal AND a 50% second-unit deal). DealHunter evaluates all available promotions order-independently and selects the one with the highest effective discount for `discount_effective`.

## Persistence (Schema v12)

The `observations` table supports SQL-level filtering via:
- `is_pro_exclusive` (INTEGER)
- `pro_price` (REAL)
- `limit_info` (TEXT)
