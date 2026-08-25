# DEALHUNTER PHASE 5B.1 — UBER EATS SURFACE DISCOVERY

**Date**: 2026-08-25
**Baseline**: DealHunter v3.0.1, Schema 14
**Method**: Android dumpsys + Web search research (no live requests to UE APIs)

---

## DISCOVERED

| Metric | Count |
|---|---|
| Total surfaces | 27 |
| Android | 18 (deeplinks/schemes from manifest) |
| Web | 9 (API endpoints + SSR surfaces) |
| CONFIRMED | 14 |
| CANDIDATE | 13 |
| BLOCKED | 0 (known WAF, but legitimate browser path remains open) |

---

## HIGH VALUE (Top 5)

1. **UE-C1 getStoreV1** — Full merchant catalog (sections, items, modifiers, pricing, availability). LIKELY COMPLETE. This is the primary data source, equivalent to Rappi's store catalog endpoint.

2. **UE-B1 __NEXT_DATA__** — Next.js SSR hydration contains structured menu/pricing data in the HTML payload. If accessible via legitimate browser, bypasses API session requirements for initial data.

3. **UE-A1 getFeedV1** — Merchant discovery by location. Algorithmic subset, not exhaustive, but primary entry point.

4. **UE-G1 Deals Feed** — Dedicated `/deals` page confirmed via Android deeplinks. Likely separate API operation or filtered getFeedV1. VERY HIGH value for DealHunter's core mission.

5. **UE-J5 + UE-J6 Deals + Category Deeplinks** — Android confirms `/deals` and `/category-feed/{type}` as first-class navigation paths, validating that promotions and category browsing are structured surfaces (not just UI overlays).

---

## IDENTITY

### Observed Fields
- `storeUuid`: URL-safe base64/UUID hybrid (e.g., `vN5-d143RhyuKDBH7Oq4Kw`) — CONFIRMED
- `itemUuid`: Same format suspected — CANDIDATE (referenced in deeplink scheme)
- `sectionId` / `categoryId`: Within getStoreV1 menu hierarchy — CANDIDATE
- `modifier_group_id`: Within getStoreV1 item modifiers — CANDIDATE

### Relationships Suspected
```
storeUuid (merchant)
  └── menuSections[] (sectionId = category)
       └── items[] (itemUuid)
            └── modifier_groups[] (modifier_group_id)
                 └── modifier_items[] (modifier_id, price)
```

### Unknowns
- Exact UUID format for items/sections/modifiers (may differ from store UUID)
- Whether `catalogId` exists as a separate concept from `storeUuid`
- UUID stability across time/menu updates
- Whether the same physical store has multiple storeUuids (delivery vs pickup vs different menus)

---

## COMMERCIAL

### Pricing
- **Location**: `items[].price` in getStoreV1 response
- **Format**: Integer (cents/smallest currency unit) + currency code
- **Overrides**: Delivery vs pickup pricing may differ
- **Fields suspected**: `price`, `originalPrice`, `discountedPrice`
- **Status**: CANDIDATE — confirmed by multiple sources, exact field names need live validation

### Promotions
- **Dedicated surface**: `/deals` deeplink CONFIRMED
- **Merchant-level**: Promo badges in feed (BOGO indicators, free delivery, discount tags)
- **Item-level**: Embedded in getStoreV1 item data
- **Types observed**: Price discount, BOGO/NxM, free item, free delivery, minimum spend
- **Status**: CANDIDATE — types confirmed by research, exact API field names need validation

### Uber One
- **Nature**: Delivery fee waiver ($0 on eligible orders), member-only promotions, possible item price differences
- **Detection**: Uber One badge on merchants, membership deeplink, `ubereatsmembershipredirect://` scheme
- **Impact**: Primarily delivery fees and eligibility; item price changes UNKNOWN
- **Status**: CANDIDATE — requires authenticated session with active membership to observe

---

## AVAILABILITY

- **Candidate**: Item-level availability flags within getStoreV1 response
- **Also**: Store-level open/closed status in feed
- **Status**: CANDIDATE — confirmed conceptually, field names need validation

---

## DEEPLINKS

### Confirmed
| Type | Pattern |
|---|---|
| Store (web) | `https://www.ubereats.com/{locale}/store/{slug}/{storeUuid}` |
| Store (native) | `ubereats://store/browse?client_id=eats&storeUUID={UUID}` |
| Item (native) | `ubereats://store/browse?client_id=eats&storeUUID={UUID}&itemUUID={UUID}` |
| Feed | `https://www.ubereats.com/{locale}/feed` |
| Search | `https://www.ubereats.com/{locale}/search` |
| Deals | `https://www.ubereats.com/{locale}/deals` |
| Category | `https://www.ubereats.com/{locale}/category-feed/{type}` |
| Near-me | `https://www.ubereats.com/{locale}/near-me/{cuisine}` |
| SEO | `https://www.ubereats.com/{locale}/{city}/food-delivery/{category}/{slug}` |
| Brand | `https://www.ubereats.com/{locale}/brand/{slug}` |
| Membership | `https://www.ubereats.com/{locale}/membership` |

---

## BLOCKED

### Android Dynamic
- **What**: Logcat/network capture of live app interactions (A1-A5 actions)
- **Reason**: NOT ATTEMPTED this phase (deferred per KISS scope)
- **Feasibility**: Rish IS available, actions are viable in next phase

### Web Direct HTTP
- **What**: All `www.ubereats.com` paths via simple HTTP client
- **Reason**: HTTP 403 from Cloudflare WAF on every attempted URL
- **Affected**: `/mx`, `/mx/feed`, `/mx/store/*`, `/near-me/*`, `/robots.txt`, `/sitemap.xml`
- **Note**: Legitimate browser + `__NEXT_DATA__` extraction is still viable

### Uber One Differential
- **What**: Observing member vs non-member pricing
- **Reason**: Requires authenticated session with active Uber One membership
- **Note**: Analogous to Rappi Pro pricing detection

---

## NEXT VALIDATION

### Exact Surfaces to Test (with common model)

1. **W3: getStoreV1 via browser** — Open a known merchant page in legitimate browser, extract `__NEXT_DATA__` JSON, map exact field names for: storeUuid, sections, items, pricing, availability, promotions
2. **W1: getFeedV1 via browser** — Load home feed, capture XHR request/response structure for merchant discovery
3. **W5: /deals via browser** — Open deals page, identify whether it uses a separate API operation or filtered getFeedV1
4. **W2: Search via browser** — Perform a search, capture operation name and response structure
5. **A1-A3: Android logcat** — Open Uber Eats → home → search → merchant, capture API hostnames and operation names from logcat/network

### Exact Questions to Answer

1. What are the exact field names for item pricing? (`price`, `priceV2`, `originalPrice`?)
2. Does getStoreV1 contain ALL menu items or does it paginate?
3. What does the deals page API response look like? Separate operation or filtered feed?
4. What is the exact UUID format for items and sections?
5. Does Uber Eats use GraphQL for any consumer-facing operations, or only REST-like POST RPC?
6. Does `__NEXT_DATA__` contain full catalog or just initial data with lazy-loading?
7. What API hostname does the Android app use? (`cn-geo1.uber.com`? `api.uber.com`? same as web?)
8. Are there rate limits / WAF differences between web API and Android API?

### Recommended Sample

- 1 known merchant (e.g., McDonald's CDMX) — to validate getStoreV1 / __NEXT_DATA__
- 1 feed load — to validate getFeedV1 discovery
- 1 deals page load — to validate promotions surface
- 1 search query — to validate search operation

Total: 4 browser actions. Maximum.

---

## ARCHITECTURAL NOTES FOR DEALHUNTER

### Web Approach (Priority)
The web `__NEXT_DATA__` SSR path is the most promising initial approach:
- Next.js renders structured JSON in HTML
- Contains store, menu, items, pricing data
- Accessible via legitimate browser rendering
- No separate API authentication needed (page load = data)
- Cloudflare WAF blocks raw HTTP but allows real browsers

### Android Approach (Secondary)
Android app uses different API infrastructure:
- Likely `cn-geo1.uber.com` or similar mobile-specific endpoints
- SSO between Uber and Uber Eats via content providers
- Rich deeplink system enables programmatic navigation to specific stores/items
- Logcat may reveal mobile-specific operation names

### Namespace Strategy (Unchanged)
- storeUuid → `UE-{storeUuid}` as store_id in DealHunter
- itemUuid → `UE-{itemUuid}` as product_id in DealHunter
- No schema migration needed (Schema 14 supports string IDs)

---

STOP.
