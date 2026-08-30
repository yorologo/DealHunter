# UBER EATS SOURCE AUTHORITY

> [!IMPORTANT]
> Historical phase snapshot. It records the evidence and constraints observed in
> that phase; it is not current operational guidance. Current RC truth is
> v3.2.0 / schema v16: Rappi and Uber acquisition are production-capable, while
> canonical matching remains shadow-only, automatic writes are OFF, human
> ground truth is insufficient and the statistical gate is `NOT_MET`.


Phase 5B.2 — Validated (2026-08-25)

---

## Primary Source Candidate: SSR Hydration (`__REACT_QUERY_STATE__`)

**Authority Level**: HIGH

### What it provides

| Data Type | Available | Completeness | Authority |
|---|---|---|---|
| Store identity (UUID, slug, city) | ✅ | COMPLETE | PRIMARY |
| Store metadata (address, geo, rating, categories) | ✅ | COMPLETE | PRIMARY |
| Store availability (isAvailable) | ✅ | COMPLETE | PRIMARY |
| Currency code | ✅ | COMPLETE | PRIMARY |
| Catalog sections (sectionUuid, subsectionUuid) | ✅ | COMPLETE (convenience) / PARTIAL (restaurant) | PRIMARY |
| Catalog items (uuid, title, price, image) | ✅ | COMPLETE (convenience) / PARTIAL (restaurant) | PRIMARY |
| Item availability (isSoldOut, isAvailable, itemAvailabilityState) | ✅ | COMPLETE | PRIMARY |
| Item pricing (centavos) | ✅ | COMPLETE | PRIMARY |
| Item promotions (promoInfo, itemLevelPromotion) | ✅ | COMPLETE | PRIMARY |
| Provider product identifier (`productUuid`) | ✅ | FIELD PRESENT; cross-store scope UNKNOWN | SUPPORTING |
| Purchase constraints (min/max quantities) | ✅ | COMPLETE | PRIMARY |
| Customization indicator (hasCustomizations) | ✅ | COMPLETE | PRIMARY |

### What it does NOT provide

| Data Type | Status | Alternative |
|---|---|---|
| Restaurant full menu (lazy-loaded) | MISSING | Requires client-side `getStoreV1` call |
| Modifier groups / customization details | MISSING | Requires item detail API |
| Historical prices | N/A | DealHunter must collect over time |
| Delivery fee / service fee details | PARTIAL | `fareInfo` present but sparse |
| Uber One pricing differential | MISSING | Requires authenticated session |
| Store hours / schedule | UNKNOWN | May be in full SSR state |

### Access Requirements

| Requirement | Status |
|---|---|
| Authentication | NOT REQUIRED |
| Session cookies | NOT REQUIRED (server sets them) |
| CSRF token | NOT REQUIRED |
| Browser User-Agent | REQUIRED (standard mobile UA works) |
| Location context | NOT REQUIRED (store UUID determines content) |
| Accept-Encoding: gzip | RECOMMENDED (responses are gzip-compressed) |
| Cloudflare challenge | NOT TRIGGERED for store pages |
| Rate limiting | UNKNOWN — not observed in validation probing |

### Request Profile

| Metric | Value |
|---|---|
| Method | GET |
| URL | `https://www.ubereats.com/mx/store/{slug}/{base64url_uuid}` |
| Response size | 462 KB (restaurant) — 820 KB (convenience with catalog) |
| Server timing | dsbe=297ms, rl=527ms |
| CDN | Cloudflare (cf-ray, DFW edge) |
| Cache-Control | `no-store, max-age=0` |
| Requests per store | 1 |

---

## Secondary Source Candidate: Sitemaps

**Authority Level**: HIGH (for discovery)

### What it provides

| Data Type | Available | Completeness |
|---|---|---|
| All MX store URLs (slug + base64url UUID) | ✅ | COMPLETE (74,328 stores) |
| Global store inventory | ✅ | COMPLETE |

### What it does NOT provide

- Store metadata (name, category, rating, etc.)
- Catalog data
- Pricing
- Availability
- Promotions

### Access Requirements

| Requirement | Status |
|---|---|
| Authentication | NOT REQUIRED |
| Rate limiting | UNKNOWN |
| Format | Gzip-compressed XML |
| Update frequency | UNKNOWN (sitemap hash `771af823` appears stable) |

### Request Profile

| Metric | Value |
|---|---|
| Method | GET |
| URLs | `robots.txt` → 26 sitemap shards |
| Total MX stores | 74,328 |
| Requests for full inventory | 27 (1 robots.txt + 26 shards) |

---

## Tertiary Source: Near-me Category Pages

**Authority Level**: MEDIUM (for category-scoped discovery)

### What it provides

| Data Type | Available | Completeness |
|---|---|---|
| Store URLs by category | ✅ | PARTIAL (~80 per category) |
| JSON-LD ItemList | ✅ | ~80 items |
| Breadcrumbs | ✅ | COMPLETE |

### Limitations

- Limited to ~80 stores per category
- Geo-dependent (based on request IP)
- Not all category slugs are valid (e.g., `convenience-store` returns 404)

---

## Tertiary Source: JSON-LD (Schema.org)

**Authority Level**: MEDIUM (for store metadata validation)

### What it provides

- Store name, address, geo coordinates
- Cuisine types
- Phone number
- Aggregate rating
- Breadcrumb hierarchy

### Limitations

- No catalog/item data in JSON-LD
- Mainly useful for cross-validating SSR data

---

## Source Ranking for DealHunter

### Strategy A: Public Web Extraction (No Authentication)

```
DISCOVERY:
  1. Sitemaps (74,328 MX stores) → COMPLETE inventory
  2. Near-me pages (~80 per category) → Category-scoped discovery
  3. Brand pages → Brand-level aggregation

CATALOG + PRICING:
  1. SSR __REACT_QUERY_STATE__ → COMPLETE for convenience/grocery
  2. SSR __REACT_QUERY_STATE__ → PARTIAL for restaurants (identity only)

IDENTITY:
  1. SSR __REACT_QUERY_STATE__ → storeUuid, productUuid, sectionUuid
  2. JSON-LD → name, address, geo, rating
  3. Sitemaps → slug, base64url UUID

PROMOTIONS:
  1. SSR __REACT_QUERY_STATE__ → itemLevelPromotion, promoInfo
  2. Deals page Redux state → feed-level promo data (limited)

AVAILABILITY:
  1. SSR __REACT_QUERY_STATE__ → isSoldOut, isAvailable, itemAvailabilityState
```

### Strategy B: Authenticated API (Future — Requires Session)

```
Would unlock:
  - getStoreV1 → Full restaurant menus (lazy-loaded items)
  - getFeedV1 → Algorithmic discovery feed
  - getSearchV1 → Search-based discovery
  - Uber One pricing differential
  - Modifier groups / customization details
```

---

## Adapter Readiness Assessment

### What is READY for adapter implementation

1. **Store discovery** via sitemaps (74,328 MX stores, 27 requests)
2. **Store page fetching** via GET (public, no auth)
3. **Catalog extraction** for convenience/grocery stores (complete in SSR)
4. **Item identity** model (uuid, productUuid, sectionUuid hierarchy)
5. **Pricing** extraction (integer centavos, MXN)
6. **Availability** extraction (isSoldOut, isAvailable)
7. **Promotion** extraction (promoInfo, itemLevelPromotion)
8. **Store metadata** (name, address, geo, rating, categories)
9. **JSON-LD** validation layer

### What is NOT ready

1. **Restaurant catalog completeness** — lazy-loaded, requires `getStoreV1` API call with session
2. **Rate limiting profile** — not measured at scale
3. **Uber One price differential** — requires authenticated Uber One session
4. **Modifier/customization details** — not in SSR catalog items
5. **Store hours** — not confirmed in SSR payload
6. **Delivery fee details** — `fareInfo` sparse

### Recommended Initial Scope

Start adapter with:
- Convenience stores (OXXO, 7-Eleven, Farmacias Guadalajara, Costco)
- These have COMPLETE catalogs in SSR
- Full pricing and availability
- Good promotion coverage
- Known product brands for cross-store comparison

Defer:
- Pure restaurant menus (require API authentication)
- Uber One pricing layer
- Modifier/customization extraction

---

## Security and Ethics Compliance

| Principle | Status |
|---|---|
| Read-only | ✅ No write operations |
| No WAF bypass | ✅ Standard browser UA only |
| No authentication bypass | ✅ Public pages only |
| No anti-bot circumvention | ✅ Standard HTTP requests |
| Respect robots.txt | ✅ `/store/*` is ALLOWED |
| No secrets | ✅ No tokens, cookies, or credentials used |
| Conservative requests | ✅ 1 request per store catalog |
| Explainable | ✅ All data from publicly rendered HTML |
