# UBER EATS CONTRACT CANDIDATES

Updated: Phase 5B.1 (2026-08-25)

---

## 1. UE-A1: Discovery (getFeedV1)

**INPUT**
- Location context (lat/lng, typically via `uev2.loc` cookie or payload).
- CSRF Token (`x-csrf-token`).
- Device / Session headers (`x-uber-device-id`).
- Session cookies (`sid`, `jwt-session`, `uev2.id.session`).

**OUTPUT**
- Array of merchant cards.
- Basic metadata: Name, UUID, estimated delivery time, rating.
- Promo badges (BOGO, discount, free delivery indicators).
- Uber One eligibility badge.
- Store open/closed status.

**COMPLETENESS**
- UNKNOWN. Feed APIs typically return algorithmic subsets, not exhaustive geospatial inventories.

**AUTH**
- WAF / Session dependent. HTTP 403 without browser context.

---

## 2. UE-A2: Search (getSearchV1) — CANDIDATE

**INPUT**
- Query text.
- Location context.
- Session cookies.

**OUTPUT**
- Matched merchants and/or items.

**COMPLETENESS**
- UNKNOWN. Depends on search algorithm coverage.

**AUTH**
- WAF / Session dependent.

---

## 3. UE-C1: Catalog (getStoreV1)

**INPUT**
- Merchant UUID (`storeUuid`).
- Location context (to validate delivery radius).
- Session cookies.

**OUTPUT**
- Nested sections (Categories/menuSections).
- Items (UUID, name, description, price, availability).
- Modifier groups (modifier_group_id → modifier_items with prices).
- Promotion indicators per item.
- Store-level metadata.

**COMPLETENESS**
- LIKELY COMPLETE. Uber Eats typically renders the entire store menu via this endpoint, grouped by sections. Large menus may lazy-load.

**AUTH**
- WAF / Session dependent.

---

## 4. UE-B1: SSR Hydration (__NEXT_DATA__) — NEW

**INPUT**
- Standard browser page load of store URL.
- No separate API authentication required.

**OUTPUT**
- `props.pageProps.store` containing structured JSON.
- Menu hierarchy, items, pricing, availability.
- Same data as getStoreV1 (rendered server-side).

**COMPLETENESS**
- LIKELY PARTIAL for large menus. Remaining data lazy-loaded via XHR.

**AUTH**
- PUBLIC (if page loads via real browser). BLOCKED via raw HTTP (403).

---

## 5. UE-E1: Item Detail (getMenuItemV1) — CANDIDATE

**INPUT**
- `itemUuid` + `storeUuid`.
- Session cookies.

**OUTPUT**
- Item details with full modifier tree.
- Pricing with all customization options.

**COMPLETENESS**
- UNKNOWN. May be redundant if getStoreV1 already contains full item data.

**AUTH**
- WAF / Session dependent.

---

## 6. UE-G1: Deals Feed — CANDIDATE

**INPUT**
- Location context.
- Session cookies.
- Possibly a variant of getFeedV1 or separate operation.

**OUTPUT**
- Merchants/items with active promotions.
- Promotion types: discount, BOGO, free item, free delivery, minimum spend.

**COMPLETENESS**
- UNKNOWN.

**AUTH**
- WAF / Session dependent.

---

## 7. UE-H1: Uber One (Conditional Pricing)

**INPUT**
- User session with active Uber One membership.

**OUTPUT**
- $0 delivery fee on eligible orders (min order required).
- Member-only promotions.
- Possibly different item prices (UNCONFIRMED).

**COMPLETENESS**
- UNKNOWN. Need live session with Uber One to observe pricing differences.

**AUTH**
- Authenticated session with active Uber One membership required.

---

## 8. UE-F1: Pricing Fields — CANDIDATE

**LOCATION**
- `items[].price` in getStoreV1 / __NEXT_DATA__.

**FORMAT**
- Integer (cents/smallest currency unit) + currency code.
- Possible fields: `price`, `priceV2`, `originalPrice`, `discountedPrice`, `overrides`.
- Delivery vs pickup pricing may differ.

**VALIDATION NEEDED**
- Exact field names.
- Whether `originalPrice` is always present or only during promotions.
- Currency representation for MXN.

---

## 9. UE-I1: Availability — CANDIDATE

**LOCATION**
- Item-level flags in getStoreV1 response.
- Store-level open/closed in feed response.

**FORMAT**
- Boolean or enum (UNKNOWN exact structure).

**VALIDATION NEEDED**
- Exact field name and values.
- Whether out-of-stock items are omitted or flagged.
