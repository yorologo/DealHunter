# Phase 5D.3: Uber Eats Provider Capability Hardening

## Overview
Phase 5D.3 evaluated the operational viability of Uber Eats across native Android, Chrome/CDP, and Hybrid architectures, subsequently adopting the `CDP_PRIMARY` transport as the most reliable, fully-featured primitive. 

The selected transport was then hardened to support multiple native capabilities, including robust catalog sync, complex restaurant paginations, and deduplication within DealHunter's existing v15 multi-provider schema.

## Transport Bake-Off Results

We evaluated alternative Android-native primitives to check whether we could avoid browser automation.

- **CDP_PRIMARY (Winner)**: 
  - *Structured Data*: Excellent. Delivers 100% exact raw JSON API payloads via network interception / fetch injection (`getStoreV1`).
  - *Completeness*: Excellent. Fully respects complex `catalogSectionOffset` pagination requirements for supermarkets.
  - *Request Cost*: Excellent. Minimal bandwidth; utilizes the genuine browser context.
- **Android Native**:
  - *Feasibility*: Poor/Blocked. Sandbox prevents reading database files without root (`com.ubercab.eats`). Network payloads are not naturally exposed in `logcat` logs. UI Automator (`uiautomator dump`) was tested but generates unscalable node crawling flows prone to breaking.

Conclusion: Chrome/CDP using `fetch` injection remains the singular viable, fully-structured acquisition model.

## Catalog Coverage Hardening

- **Supermarkets**: (e.g., OXXO, Soriana, 7-Eleven). Successfully parsed and handled standard pagination.
- **Restaurants**: (e.g., Tony Pepperoni, Pizzahead, Da Fabio Trattoria Pizzeria Bar). 
  - We confirmed that restaurant menus are successfully handled natively by `UberEatsParser` relying on `catalogSectionsMap`.
  - Pagination gracefully breaks upon completion (offset logic).
  - Average yield: 20-100+ items immediately per response without infinite-looping.

## Price Intelligence & Promotions

- We analyzed the discrepancy between `price` and `purchaseInfo.purchaseOptions[0].purchasePriceV2.base.low`.
- DealHunter's `UberEatsParser` was successfully upgraded to natively extract the `reference_price` from `purchasePriceV2.base.low` (or fallback to `priceTagline.accessibilityText`), accurately revealing original prices against `discount_price` conditions for promotions (e.g. 15% discount tags).
- Detected active promotion signatures (`promotion_uuid`) mapped against `discount_promotion` schema fields.

## DealHunter Multi-Provider Integration (Schema v15)

- Live multi-provider sync was successfully tested.
- **UUID Deduplication**: `ON CONFLICT (provider, store_id, product_id)` correctly handles multiple syncs over time.
- **Run History Check**: A double-sync (Run 1 -> Run 2) over the exact same target stores successfully resulted in deduplicated products while accurately persisting historical `observations`. 
- **Integrity**: DealHunter v3's core `deals`, `search_local` queries and UI safely isolate and filter `provider="uber_eats"` conditions.

## Deeplink Viability
We verified Android deeplinks via Termux `am start`:
- `ubereats://store/{uuid}`
- `https://www.ubereats.com/store/{slug}/{uuid}`
Both deep links open the correct store accurately within the Uber Eats application, enabling robust "View Deal" intent mappings for the UI.

## Conclusion
The Uber Eats integration is now a mature, fully-proven pipeline that honors DealHunter's strict historical price observation engine natively alongside Rappi.
