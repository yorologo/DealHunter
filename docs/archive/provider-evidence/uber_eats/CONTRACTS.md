# UBER EATS VALIDATED CONTRACTS

Phase 5B.2 — Surface Validation (2026-08-25)

---

## 1. UE-C1: Store Catalog via SSR (`__REACT_QUERY_STATE__`)

**STATUS**: CONFIRMED_CONTRACT

**ACCESS METHOD**: `GET https://www.ubereats.com/mx/store/{slug}/{base64url_uuid}`

**AUTH LEVEL**: PUBLIC (standard browser User-Agent, no session required)

**FRAMEWORK**: Fusion.js (Uber internal) — NOT Next.js

**DATA LOCATION**: `<script id="__REACT_QUERY_STATE__">` embedded in HTML

**ENCODING**: Unicode-escaped JSON (`\u0022` = `"`)

**VALIDATED MERCHANTS**:

| Merchant | UUID | Type | Items | Size |
|---|---|---|---|---|
| 7 Eleven (ISSTE Zapopan) | `72ebad37-1063-518d-b667-a4bf9d2fbe00` | Convenience | 40 | 820 KB |
| OXXO (Laureles GDL) | `95d42fe0-a4ad-5d80-b371-9fb3a428e124` | Convenience | 40 | 783 KB |
| Chili's (Galerías Insurgentes) | `a24b5931-99f4-48bc-af90-5808ed3d7556` | Restaurant | 0 (lazy) | 462 KB |

**CATALOG ITEM SCHEMA** (validated):
```json
{
  "uuid": "67870a59-b875-49be-843c-602c9d6f5e6c",
  "title": "Topo Chico · Agua mineral natural (1,5 L)",
  "price": 3950,
  "imageUrl": "https://tb-static.uber.com/prod/image-proc/...",
  "spanCount": 1,
  "displayType": "GRID",
  "isSoldOut": false,
  "hasCustomizations": false,
  "isAvailable": true,
  "itemAvailabilityState": "AVAILABLE",
  "sectionUuid": "7824731d-b6fd-52c3-b7d1-48859a8a997e",
  "subsectionUuid": "cf860f35-0870-475e-b8a9-149f0d87baf0",
  "purchaseInfo": {
    "purchaseOptions": [{
      "soldByUnit": { "measurementType": "MEASUREMENT_TYPE_COUNT" },
      "quantityConstraintsV2": {
        "minPermitted": { "base": 100000, "exponent": -5 },
        "maxPermitted": { "base": 25000000, "exponent": -5 }
      }
    }]
  },
  "productInfo": {
    "productUuid": "c66f0df5-d72a-5cd7-a863-08985aed5c31"
  },
  "promoInfo": {
    "promotionUUID": "debe88e8-9a26-4e61-bc9f-be0d07228704"
  },
  "itemLevelPromotion": {
    "type": "multiSKUFlatPromotion",
    "multiSKUFlatPromotion": {
      "collectionUuid": "...",
      "promotionUuid": "...",
      "itemPromotionTag": {
        "text": "Ahorra $25 en pedidos $149+"
      }
    }
  },
  "quickAddConfig": { "shouldShow": true },
  "catalogItemAnalyticsData": { "catalogSectionItemPosition": 0 }
}
```

**STORE IDENTITY FIELDS** (validated):
```json
{
  "uuid": "72ebad37-1063-518d-b667-a4bf9d2fbe00",
  "storeUuid": "72ebad37-1063-518d-b667-a4bf9d2fbe00",
  "slug": "7-eleven-isste-zapopan",
  "title": "7 Eleven 🛒(ISSTE ZAPOPAN)",
  "citySlug": "guadalajara",
  "cityId": 204,
  "currencyCode": "MXN",
  "isAvailable": true,
  "latitude": 20.71925,
  "longitude": -103.386878,
  "categories": ["Express", "Retail"],
  "rating": { "ratingValue": 5, "reviewCount": 29 }
}
```

**PRICING**:
- Format: Integer in centavos (MXN cents). `3950` = $39.50 MXN
- Currency: Explicit `currencyCode: "MXN"`
- No `originalPrice` / `discountedPrice` distinction at item level (price changes via promotions)

**PROMOTIONS**:
- `promoInfo.promotionUUID`: Links item to active promotion
- `itemLevelPromotion.type`: Promotion classification (`multiSKUFlatPromotion`)
- `itemLevelPromotion.multiSKUFlatPromotion.itemPromotionTag.text`: Human-readable promo text
- 8/40 items had active promotions in the 7-Eleven sample (20%)
- 14/40 items had promotions in the OXXO sample (35%)

**AVAILABILITY**:
- `isSoldOut`: Boolean (explicit)
- `isAvailable`: Boolean (explicit)
- `itemAvailabilityState`: Enum (`"AVAILABLE"`)
- Dual-field availability: both `isSoldOut` AND `isAvailable` present on every item

**COMPLETENESS**:
- Convenience stores (7-Eleven, OXXO): **COMPLETE** — 40 items with full catalog in SSR
- Restaurants (Chili's): **PARTIAL** — store identity present but `catalogSectionsMap: null`, `sections: []`. Catalog requires client-side lazy loading via `getStoreV1` API call

**REPRODUCIBILITY**: Confirmed across 2 runs, 3 merchants, 2 store types

---

## 2. UE-B1: JSON-LD Schema.org Data

**STATUS**: CONFIRMED_CONTRACT

**ACCESS METHOD**: Same as UE-C1 (embedded in store pages)

**LOCATION**: `<script type="application/ld+json">`

**VALIDATED SCHEMAS**:

### Restaurant Schema
```json
{
  "@context": "https://schema.org",
  "@type": "Restaurant",
  "name": "7 Eleven 🛒(ISSTE ZAPOPAN)",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "guadalajara",
    "addressRegion": "LATAM",
    "postalCode": "45150"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 20.71925,
    "longitude": -103.386878
  },
  "servesCuisine": ["Express", "Retail", "Cuidado personal", "Farmacia"],
  "telephone": "+528110486367",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 5,
    "reviewCount": 29
  }
}
```

### BreadcrumbList
```json
{
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "position": 1, "name": "México", "item": "https://www.ubereats.com/mx" },
    { "position": 2, "name": "7 Eleven 🛒(ISSTE ZAPOPAN)", "item": "https://www.ubereats.com/mx/store/..." }
  ]
}
```

### FAQPage
- 7 auto-generated Q&A items per store

**COMPLETENESS**: COMPLETE for store identity/metadata. No item-level JSON-LD.

---

## 3. UE-S1: Sitemap Store Discovery

**STATUS**: CONFIRMED_CONTRACT

**ACCESS METHOD**: `GET https://www.ubereats.com/robots.txt` → Sitemap URLs

**SITEMAP INDEX**: `https://www.ubereats.com/sitemap-index-771af823.xml.gz`

**STORE SITEMAPS**: 26 shards (`sitemap-store-771af823-000.xml.gz` through `025`)

**FORMAT**: Gzip-compressed XML

**MEXICO STORES**: **74,328** total across all 26 shards (~2,800-2,930 per shard)

**URL FORMAT**: `https://www.ubereats.com/mx/store/{slug}/{base64url_uuid}`

**COMPLETENESS**: COMPLETE — contains all indexed Uber Eats merchants in Mexico

**REPRODUCIBILITY**: Confirmed across 2 runs

**AUTH**: PUBLIC (no authentication required)

---

## 4. UE-N1: Near-me Category Discovery

**STATUS**: CONFIRMED_CONTRACT

**ACCESS METHOD**: `GET https://www.ubereats.com/mx/near-me/{category}`

**VALIDATED CATEGORIES**:

| Category | Status | Store Links | Size |
|---|---|---|---|
| `fast-food` | 200 OK | 80 | 1.08 MB |
| `grocery` | 200 OK | ~80 | 1.09 MB |
| `pizza` | 200 OK | ~80 | 1.06 MB |
| `convenience-store` | 404 | 0 | 443 KB |

**DATA AVAILABLE**:
- Store links with slug + base64url UUID
- JSON-LD `ItemList` with up to 80 stores
- JSON-LD `BreadcrumbList`
- JSON-LD `FAQPage`

**COMPLETENESS**: PARTIAL — limited to ~80 stores per category, geo-dependent

**AUTH**: PUBLIC (no session required)

**NOTE**: Returns results without location context (uses GDL IP geolocation as default)

---

## 5. UE-BR1: Brand Pages

**STATUS**: CONFIRMED_CONTRACT

**ACCESS METHOD**: `GET https://www.ubereats.com/mx/brand/{brand_slug}`

**VALIDATED BRANDS**:

| Brand | Status | Size | Cache |
|---|---|---|---|
| `mcdonalds` | 200 OK | 379 KB | `public, max-age=86400` |
| `starbucks` | 200 OK | 400 KB | `public, max-age=86400` |

**DATA AVAILABLE**: Brand aggregation page, `FAQPage` JSON-LD

**COMPLETENESS**: PARTIAL — aggregation metadata, not individual store catalogs

**AUTH**: PUBLIC

---

## 6. UE-D1: Deals Page

**STATUS**: PARTIAL_CONTRACT

**ACCESS METHOD**: `GET https://www.ubereats.com/mx/deals`

**RESPONSE**: 200 OK, ~633 KB

**DATA AVAILABLE**:
- `__REDUX_STATE__`: 149 KB with `feed.cachedResponses` containing 20 store UUIDs
- `__REACT_QUERY_STATE__`: 2.3 KB (minimal)
- 64 occurrences of "promotion" in Redux state
- 20 store UUIDs with rating data

**COMPLETENESS**: PARTIAL — feed is algorithmic/geo-dependent, requires location context for useful results. Without location cookie, returns generic MX deals.

**AUTH**: PUBLIC (page loads, but content is location-dependent)

---

## 7. UE-A1: Discovery Feed API (`getFeedV1`)

**STATUS**: BLOCKED

**PATH**: `POST https://www.ubereats.com/_p/api/getFeedV1`

**RESPONSE**: HTTP 403, 19 bytes (Cloudflare WAF)

**REQUIRED CONTEXT**: `x-csrf-token`, session cookies (`sid`, `jwt-session`), `x-uber-device-id`

**REPRODUCIBILITY**: Confirmed blocked across 2 runs

---

## 8. UE-C1-API: Store Catalog API (`getStoreV1`)

**STATUS**: BLOCKED

**PATH**: `POST https://www.ubereats.com/_p/api/getStoreV1`

**RESPONSE**: HTTP 403, 19 bytes (Cloudflare WAF)

**NOTE**: Data IS accessible via SSR hydration (see contract #1), making the direct API call unnecessary for most DealHunter use cases

---

## 9. UE-A2: Search API (`getSearchV1`)

**STATUS**: BLOCKED

**PATH**: `POST https://www.ubereats.com/_p/api/getSearchV1`

**RESPONSE**: HTTP 403, 19 bytes

**WEB PAGE**: `/mx/search` → 307 redirect to `def.uber.com/es/challenge` (WAF)

---

## 10. UE-J-ANDROID: Android Deeplinks

**STATUS**: CONFIRMED_CONTRACT

**APP**: `com.ubercab.eats` installed, 101 intent filters

**SHIZUKU**: Available via `rish`

| Deeplink | Resolves To | Status |
|---|---|---|
| `ubereats://store/browse?client_id=eats` | `LauncherActivity` | CONFIRMED |
| `ubereats://feed` | `LauncherActivity` | CONFIRMED |
| `ubereats://search` | `LauncherActivity` | CONFIRMED |
| `ubereats://promo/apply?client_id=eats&promoCode=TEST` | `LauncherActivity` | CONFIRMED |
| `https://www.ubereats.com/mx/*` | `ResolverActivity` | PARTIAL (disambiguated) |

**CONTENT PROVIDER**: `content://com.ubercab.eats.sso.provider/` → BLOCKED (signature-protected)

---

## 11. UE-J1: Landing/Membership Pages

**STATUS**: CONFIRMED_CONTRACT

| Page | Status | Size | Data |
|---|---|---|---|
| `/mx` | 200 | 303 KB | `__REDUX_STATE__`, JSON-LD `WebSite`, Schema.org `SearchAction` |
| `/mx/membership` | 200 | 585 KB | `__REDUX_STATE__` |
| `/mx/deals` | 200 | 633 KB | `__REDUX_STATE__` with feed data |

---

## REJECTED SURFACES

| Surface | Tested URL | Status | Reason |
|---|---|---|---|
| Sitemap.xml (root) | `/sitemap.xml` | 404 | Does not exist at root; use `robots.txt` sitemaps |
| City pages | `/mx/city/ciudad-de-mexico` | 404 | Not a valid URL pattern for MX |
| Near-me (convenience) | `/mx/near-me/convenience-store` | 404 | Category slug not supported |
| Food-delivery SEO | `/mx/food-delivery/hamburguesas/ciudad-de-mexico` | 301→404 | Redirects to non-existent path |
| SSO Provider | `content://com.ubercab.eats.sso.provider/` | BLOCKED | Signature-protected |
| `__NEXT_DATA__` | Store pages | ABSENT | Uber Eats uses Fusion.js, NOT Next.js |
