# UBER EATS IDENTITY MAP

Phase 5B.2 discovery snapshot (2026-08-25), corrected against the current
evidence audit on 2026-08-29.

---

## UUID Format

Uber Eats uses two UUID representations:

### Full UUID representation
- Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (RFC 4122)
- Example: `a24b5931-99f4-48bc-af90-5808ed3d7556`
- Found in: `__REACT_QUERY_STATE__`, JSON-LD, API responses
- Scope: provider-specific; entity scope depends on the field.

### URL-safe Base64 UUID
- Format: 22-character base64url-encoded binary UUID
- Example: `oktZMZn0SLyvkFgI7T11Vg`
- Found in: URL paths, sitemaps
- Relationship: Direct base64url encoding of the 16-byte UUID binary
- Reversible: `base64url_decode("oktZMZn0SLyvkFgI7T11Vg")` → `a24b5931-99f4-48bc-af90-5808ed3d7556`

### Confirmed (Validated with real data)

| Field | Format | Example | Source | Stability |
|---|---|---|---|---|
| `storeUuid` | UUID v5 | `72ebad37-1063-518d-b667-a4bf9d2fbe00` | `__REACT_QUERY_STATE__`, JSON-LD | STABLE — appears in sitemaps |
| `uuid` (store) | UUID v5 | `a24b5931-99f4-48bc-af90-5808ed3d7556` | `__REACT_QUERY_STATE__` | STABLE — same as storeUuid |
| `slug` | lowercase-hyphenated | `chilis-galerias-insurgentes` | URL path, `__REACT_QUERY_STATE__` | SEMI-STABLE — may change |
| `citySlug` | lowercase-hyphenated | `mexico-city`, `guadalajara` | `__REACT_QUERY_STATE__` | STABLE |
| `cityId` | integer | `204` | `__REACT_QUERY_STATE__` | STABLE |
| `sectionUuid` | UUID | `7824731d-b6fd-52c3-b7d1-48859a8a997e` | catalogItems[].sectionUuid | PER-STORE |
| `subsectionUuid` | UUID | `cf860f35-0870-475e-b8a9-149f0d87baf0` | catalogItems[].subsectionUuid | PER-STORE |
| `itemUuid` (catalog) | UUID | `67870a59-b875-49be-843c-602c9d6f5e6c` | catalogItems[].uuid | PER-STORE |
| `productUuid` | UUID | `c66f0df5-d72a-5cd7-a863-08985aed5c31` | catalogItems[].productInfo.productUuid | PROVIDER PRODUCT ID; cross-store scope unproven |
| `promotionUUID` | UUID | `debe88e8-9a26-4e61-bc9f-be0d07228704` | catalogItems[].promoInfo.promotionUUID | TEMPORAL |
| `collectionUuid` | UUID | `c335215c-c9f5-4864-9ceb-6a6f2760bf6f` | itemLevelPromotion.multiSKUFlatPromotion | TEMPORAL |

---

## Provider Identity Hierarchy

```
storeUuid (= uuid)
  ├── slug
  ├── citySlug / cityId
  ├── sections[] (sectionUuid)
  │     └── subsections[] (subsectionUuid)
  │           └── catalogItems[] (uuid)
  │                 ├── productInfo.productUuid  ← PROVIDER-SPECIFIC EVIDENCE
  │                 ├── promoInfo.promotionUUID
  │                 └── itemLevelPromotion.collectionUuid
  └── promotions[] (promotionUUID)
```

### Key Distinction: itemUuid vs productUuid

- `uuid` (in catalogItems): Store-specific item instance ID
- `productUuid`: provider-specific product identifier observed in raw catalog
  data. The audited corpus did not demonstrate that it is stable across stores.

Neither UUID is proof that a Rappi and Uber listing are the same commercial
product. DealHunter preserves both as raw/provider evidence.

---

## URL Identity Pattern

```
https://www.ubereats.com/{locale}/store/{slug}/{base64url_uuid}
```

Examples:
- `https://www.ubereats.com/mx/store/chilis-galerias-insurgentes/oktZMZn0SLyvkFgI7T11Vg`
- `https://www.ubereats.com/mx/store/7-eleven-isste-zapopan/cuutNxBjUY22Z6S_nS--AA`
- `https://www.ubereats.com/mx/store/oxxo-laureles-gdl/ldQv4KStXYCzcZ-zpCjhJA`

### Android Deeplink Identity

```
ubereats://store/browse?client_id=eats&storeUUID={uuid}
ubereats://store/browse?client_id=eats&storeUUID={uuid}&itemUUID={item_uuid}
```

---

## Locale / Market Codes

| Locale | Market |
|---|---|
| `mx` | Mexico (Spanish) |
| `mx-en` | Mexico (English) — confirmed 404 on city pages |

---

## Session Identity (Observed in Headers)

| Cookie | Purpose | Scope |
|---|---|---|
| `uev2.id.session` | Session ID | Per-visit |
| `uev2.id.session_v2` | Session ID v2 | Per-visit |
| `jwt-session` | JWT session token | 24h expiry |
| `dId` | Device ID | 1 year expiry |
| `marketing_vistor_id` | Marketing visitor | 1 year expiry |
| `__cf_bm` | Cloudflare bot management | 30 min expiry |

---

## Identity Unknowns

1. Whether `productUuid` is stable across time and store changes; current evidence is insufficient
2. Whether section/subsection UUIDs persist across menu updates
3. Exact mapping of base64url UUID ↔ canonical UUID for all entity types
4. Whether menu UUIDs differ between delivery and pickup modes
