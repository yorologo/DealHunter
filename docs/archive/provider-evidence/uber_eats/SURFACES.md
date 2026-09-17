# UBER EATS SURFACES INVENTORY

> [!IMPORTANT]
> Historical phase snapshot. It records the evidence and constraints observed in
> that phase; it is not current operational guidance. Current RC truth is
> v3.2.0 / schema v16: Rappi and Uber acquisition are production-capable, while
> canonical matching remains shadow-only, automatic writes are OFF, human
> ground truth is insufficient and the statistical gate is `NOT_MET`.


Phase 5B.1 — Surface Discovery (2026-08-25)
Phase 5B.2 — Surface Validation (2026-08-25)

---

## ANDROID RECON

### Environment

| Field | Value |
|---|---|
| Package | `com.ubercab.eats` |
| Version | 6.336.10003 (112185638) |
| minSdk | 29 |
| targetSdk | 36 |
| Last Update | 2026-08-19 |
| Rish/Shizuku | AVAILABLE |
| Also installed | `com.ubercab` (Uber rides) |

### Content Providers (interesting)

| Provider | Notes |
|---|---|
| `SSOContentProvider` | First-party SSO between Uber/UberEats — shared auth |
| `SSOEligibilityContentProvider` | SSO eligibility check |
| `DeviceSessionsContentProvider` | Device session state |

### Registered Schemes

| Scheme | Purpose |
|---|---|
| `ubereats://` | Native deeplink, generic handler via `LauncherActivity` |
| `uber_share://` | Share/clipboard actions (copy, cancel) |
| `ubereatsmembershipredirect://` | Uber One membership redirect |
| `uber-wisdom-bugreport://` | Internal bug reporter |
| `uber-dragon-crawl-e2e://` | Internal E2E crawl test |
| `braintree-paypal-connect.com.ubercab.eats` | PayPal payment |
| `braintree-paypal-connect-fallback.com.ubercab.eats` | PayPal fallback |
| `com.ubercab.eats.payment.provider.callback` | Payment provider callback |

### Verified Web Domains (App Links)

- `www.ubereats.com` ✓
- `ubereats.com` ✓
- `beta.ubereats.com` ✓
- `ubereats.app.link` (Branch.io)
- `ubereats-alternate.app.link` (Branch.io)
- `ubereats.bttn.io` (button.io shortlinks)
- `eats.sng.link` (Singular attribution)
- `a.uber.com` (Uber shortlinks)
- `e.uber.com` (Uber Eats shortlinks)
- `auth.uber.com` / `auth3.uber.com` (Auth)
- `account.uber.com` / `accounts.uber.com` (Account)
- `biz-eats.uber.com` / `mbiz.uber.com` (Business)
- `payment-providers.uber.com` (Payment)
- `referrals.uber.com` (Referrals)

---

## ANDROID DEEPLINK PATHS (DealHunter-relevant)

Extracted from `dumpsys package` intent filters on `www.ubereats.com` / `ubereats.com`.

### UE-J1: Store Deeplink
- **Pattern**: `/store/{slug}/{storeUuid}`
- **Also**: `/{locale}/store/{slug}/{storeUuid}`
- **Example**: `https://www.ubereats.com/mx/store/mcdonalds-centro/vN5-d143RhyuKDBH7Oq4Kw`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: HIGH — direct navigation to merchant, contains storeUuid in path

### UE-J2: Product/Brand Deeplink
- **Pattern**: `/product/b/{id}`
- **Also**: `/{locale}/product/b/{id}`
- **Status**: CANDIDATE
- **DealHunter Value**: MEDIUM — product-level linking

### UE-J3: Feed Deeplink
- **Pattern**: `/feed`, `/{locale}/feed`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: HIGH — home feed entry

### UE-J4: Search Deeplink
- **Pattern**: `/search`, `/{locale}/search`
- **Also**: `/search-suggestions`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: HIGH — merchant/product search

### UE-J5: Deals Deeplink
- **Pattern**: `/deals`, `/{locale}/deals`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: VERY HIGH — dedicated promotions page

### UE-J6: Category Feed Deeplink
- **Pattern**: `/category-feed/{type}`, `/category-feed/shop`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: HIGH — category-level browsing, "shop" = grocery/convenience

### UE-J7: Near-me / SEO Deeplink
- **Pattern**: `/near-me/{cuisine}`, `/{locale}/near-me/{cuisine}`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: MEDIUM — geo-based discovery by cuisine type

### UE-J8: Food Delivery SEO Pages
- **Pattern**: `/{city}/food-delivery/{category}/{slug}`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: HIGH — SEO-indexed store pages, possible static extraction

### UE-J9: Membership Deeplink
- **Pattern**: `/membership`, `/{locale}/membership`
- **Also**: `ubereatsmembershipredirect://` scheme
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: MEDIUM — Uber One context detection

### UE-J10: Brand Deeplink
- **Pattern**: `/brand/{slug}`, `/{locale}/brand/{slug}`
- **Status**: CONFIRMED_DYNAMIC
- **DealHunter Value**: MEDIUM — brand pages aggregate stores

### UE-J11: Aisle Feed
- **Pattern**: `/aisle-feed`
- **Status**: CANDIDATE
- **DealHunter Value**: HIGH — grocery aisle browsing (possible catalog surface)

### UE-J12: Venue Deeplink
- **Pattern**: `/venue`, `/{locale}/venue`
- **Status**: CANDIDATE
- **DealHunter Value**: LOW — unknown purpose, possibly events

### UE-J13: Restaurant Rewards
- **Pattern**: `/restaurant-rewards`, `/{locale}/restaurant-rewards`
- **Status**: CANDIDATE
- **DealHunter Value**: MEDIUM — loyalty/reward programs per merchant

### UE-J14: XLB Pharma
- **Pattern**: `/xlb/pharma`, `/{locale}/xlb/pharma`
- **Status**: CANDIDATE
- **DealHunter Value**: LOW (not a DealHunter priority vertical yet)

### UE-J15: Closest
- **Pattern**: `/closest/{slug}`, `/{locale}/closest/{slug}`
- **Status**: CANDIDATE
- **DealHunter Value**: MEDIUM — nearest store by type

### UE-J16: Feeds (plural)
- **Pattern**: `/feeds/{type}`, `/{locale}/feeds/{type}`
- **Status**: CANDIDATE
- **DealHunter Value**: HIGH — additional feed types beyond main feed

### UE-J17: Lists
- **Pattern**: `/lists/{id}`
- **Status**: CANDIDATE
- **DealHunter Value**: LOW — curated lists, possibly editorial

### UE-J18: Uber Eats Native Deeplink
- **Scheme**: `ubereats://store/browse?client_id=eats&storeUUID={UUID}`
- **Item variant**: `ubereats://store/browse?client_id=eats&storeUUID={UUID}&itemUUID={UUID}`
- **Promo variant**: `ubereats://promo/apply?client_id=eats&promoCode={CODE}`
- **Status**: CONFIRMED_DYNAMIC (from community/search)
- **DealHunter Value**: HIGH — direct app navigation, confirms UUID scheme

---

## WEB API SURFACES

### UE-A1: Discovery Feed (getFeedV1)
- **Status**: CONFIRMED_STATIC (documented) / BLOCKED_BY_METHOD (direct HTTP → 403)
- **Path**: `POST https://www.ubereats.com/_p/api/getFeedV1`
- **Auth Level**: SESSION_REQUIRED (cookies: `sid`, `jwt-session`, `uev2.id.session`)
- **Headers**: `x-csrf-token`, `x-uber-device-id`
- **Input**: Location context (lat/lng via `uev2.loc` cookie or payload)
- **Output**: Array of merchant cards (name, UUID, ETA, rating, basic promo badges)
- **Completeness**: UNKNOWN — feeds typically return algorithmic subsets, not exhaustive inventory
- **DealHunter Value**: HIGH — primary merchant discovery surface
- **Note**: WAF/Cloudflare blocks non-browser clients

### UE-A2: Search (getSearchV1)
- **Status**: CANDIDATE
- **Path**: `POST https://www.ubereats.com/_p/api/getSearchV1` (hypothesized)
- **Auth Level**: SESSION_REQUIRED
- **Input**: Query text + location
- **Output**: Merchant/item matches
- **DealHunter Value**: HIGH — alternative discovery for specific merchants/items
- **Note**: Search suggestion endpoint possibly separate

### UE-C1: Store Catalog (getStoreV1)
- **Status**: CONFIRMED_STATIC
- **Path**: `POST https://www.ubereats.com/_p/api/getStoreV1`
- **Auth Level**: SESSION_REQUIRED
- **Input**: `storeUuid` + location context
- **Output**: Full menu hierarchy (sections → items → modifier_groups), pricing, availability
- **Completeness**: LIKELY COMPLETE — renders full merchant menu
- **DealHunter Value**: VERY HIGH — primary catalog/pricing surface
- **Pricing format**: Integers (cents/smallest currency unit) + currency code

### UE-E1: Item Detail (getMenuItemV1)
- **Status**: CANDIDATE
- **Path**: `POST https://www.ubereats.com/_p/api/getMenuItemV1` (hypothesized)
- **Auth Level**: SESSION_REQUIRED
- **Input**: `itemUuid` + `storeUuid`
- **Output**: Item detail with modifiers, customization groups, pricing
- **DealHunter Value**: MEDIUM — may be embedded in getStoreV1

### UE-B1: SSR Hydration (__NEXT_DATA__)
- **Status**: CONFIRMED_DYNAMIC
- **Location**: `<script id="__NEXT_DATA__" type="application/json">` in HTML
- **Auth Level**: PUBLIC (if page loads) / BLOCKED_BY_METHOD (403 without browser)
- **Framework**: Next.js
- **Contains**: `props.pageProps.store`, menu hierarchy, items, pricing
- **DealHunter Value**: VERY HIGH — if accessible, contains full structured data without separate API call
- **Note**: May be partial — large menus lazy-load remaining via XHR

### UE-B2: Redux SSR State (__REDUX_STATE__)
- **Status**: CONFIRMED_DYNAMIC (previously documented)
- **Location**: Embedded in initial HTML shell
- **Auth Level**: PUBLIC
- **Role**: Bootstraps application state
- **DealHunter Value**: LOW — delegates to client-side hydration, not a direct data source

### UE-G1: Deals Feed
- **Status**: CANDIDATE
- **Path**: `/deals` (deeplink confirmed), API endpoint unknown
- **DealHunter Value**: VERY HIGH — dedicated promotions surface
- **Note**: Likely uses a variant of getFeedV1 with promotion filters, or a separate getDealsFeedV1

### UE-G2: Merchant Promotions
- **Status**: CANDIDATE
- **Source**: Embedded in getStoreV1 response (promo badges, BOGO indicators)
- **Types observed** (from search): price discount, BOGO/NxM, free item, free delivery
- **DealHunter Value**: HIGH — promotion detail per merchant

### UE-H1: Uber One (Conditional Pricing)
- **Status**: CANDIDATE
- **Mechanism**: Session-dependent pricing differentiation
- **Known effects**: $0 delivery fee on eligible orders, member-only promotions, possible item price differences
- **Detection**: Uber One badge on merchants, membership-specific API fields
- **DealHunter Value**: HIGH — conditional pricing layer (analogous to Rappi Pro)
- **Note**: Requires authenticated session with active membership to observe price differences

### UE-D1: Category Taxonomy
- **Status**: CANDIDATE
- **Sources**: 
  - `/category-feed/{type}` (deeplink)
  - `menuSections` in getStoreV1 response
  - `/near-me/{cuisine}` (SEO pages)
- **DealHunter Value**: HIGH — structured category browsing
- **Note**: Merchant-defined categories (via Menu Maker) — no universal taxonomy guaranteed

### UE-I1: Availability
- **Status**: CANDIDATE
- **Source**: Embedded in getStoreV1 response (item-level availability flags)
- **Also**: Store open/closed status in feed
- **DealHunter Value**: HIGH — tracks availability changes

### UE-F1: Pricing Structure
- **Status**: CANDIDATE (partially confirmed via search research)
- **Location**: `items[].price` in getStoreV1 response
- **Format**: Integer (cents) + currency code
- **Fields suspected**: `price`, `overrides` (delivery vs pickup), `originalPrice` / `discountedPrice`
- **DealHunter Value**: VERY HIGH — core pricing data

---

## IDENTITY FIELDS

### Observed / Suspected

| Field | Format | Example | Source |
|---|---|---|---|
| storeUuid | URL-safe base64 / UUID hybrid | `vN5-d143RhyuKDBH7Oq4Kw` | URL path, getStoreV1 |
| itemUuid | Same format (suspected) | unknown | getStoreV1 items, deeplink |
| sectionId / categoryId | UUID or string | unknown | getStoreV1 menuSections |
| modifier_group_id | UUID or string | unknown | getStoreV1 modifier_groups |
| brandId | slug or UUID | unknown | `/brand/{slug}` path |

### Relationships (Hypothesized)

```
storeUuid
  └── menuSections[] (sectionId)
       └── items[] (itemUuid)
            └── modifier_groups[] (modifier_group_id)
                 └── modifier_items[] (modifier_id)
```

### Unknowns

- Exact format of item/section/modifier UUIDs (might differ from store UUID)
- Whether catalog ID is separate from store UUID
- Scope of UUID stability across sessions/time
- Whether menu structure IDs are stable across store updates

---

## BLOCKED SURFACES

### Android Dynamic (Logcat/Network)
- **Status**: NOT ATTEMPTED this phase
- **Reason**: Requires logcat + app interaction; deferred for next validation
- **Note**: Rish IS available, so A1-A5 actions are feasible in next phase

### Web Direct HTTP
- **Status**: BLOCKED_BY_METHOD
- **Reason**: All `www.ubereats.com` paths return HTTP 403 via Cloudflare WAF
- **Affected**: `/mx`, `/mx/feed`, `/mx/store/*`, `/near-me/*`, `/robots.txt`, `/sitemap.xml`
- **Note**: Legitimate browser access is viable; automated headless HTTP is blocked

### Uber One Price Differential
- **Status**: BLOCKED_BY_AUTH
- **Reason**: Requires active Uber One membership session to observe price differences
- **Note**: DealHunter should detect Uber One status conceptually (like Rappi Pro)

---

## SURFACE SUMMARY TABLE (5B.2 Validated)

| ID | Name | Source | 5B.1 Status | 5B.2 Status | DH Value |
|---|---|---|---|---|---|
| UE-A1 | Discovery Feed API | Web API | CONFIRMED | **BLOCKED** (403) | HIGH |
| UE-A2 | Search API | Web API | CANDIDATE | **BLOCKED** (403) | HIGH |
| UE-B1 | __NEXT_DATA__ hydration | Web SSR | CONFIRMED | **REJECTED** (Fusion.js, not Next.js) | N/A |
| UE-B1r | __REACT_QUERY_STATE__ | Web SSR | (new) | **CONFIRMED_CONTRACT** | **VERY HIGH** |
| UE-B2 | __REDUX_STATE__ | Web SSR | CONFIRMED | **CONFIRMED** (identity only, no catalog) | LOW |
| UE-C1 | Store Catalog (SSR) | Web SSR | CONFIRMED | **CONFIRMED_CONTRACT** (convenience=COMPLETE, restaurant=PARTIAL) | **VERY HIGH** |
| UE-C1-API | Store Catalog API | Web API | CONFIRMED | **BLOCKED** (403) | HIGH |
| UE-D1 | Category Taxonomy | Web multi | CANDIDATE | **CONFIRMED** (via sectionUuid hierarchy) | HIGH |
| UE-E1 | Item Detail API | Web API | CANDIDATE | **BLOCKED** (403) | MEDIUM |
| UE-F1 | Pricing Structure | Web SSR | CANDIDATE | **CONFIRMED_CONTRACT** (integer centavos) | **VERY HIGH** |
| UE-G1 | Deals Page | Web SSR | CANDIDATE | **PARTIAL_CONTRACT** (Redux state, geo-dependent) | HIGH |
| UE-G2 | Merchant Promotions | Web SSR | CANDIDATE | **CONFIRMED_CONTRACT** (itemLevelPromotion) | **HIGH** |
| UE-H1 | Uber One Pricing | Session | CANDIDATE | **BLOCKED** (requires Uber One session) | HIGH |
| UE-I1 | Availability | Web SSR | CANDIDATE | **CONFIRMED_CONTRACT** (isSoldOut + isAvailable + state) | **VERY HIGH** |
| UE-J1 | Store Deeplink (web) | Android | CONFIRMED | **CONFIRMED** (resolves via ResolverActivity) | HIGH |
| UE-J3 | Feed Deeplink | Android | CONFIRMED | **CONFIRMED** (ubereats://feed → LauncherActivity) | HIGH |
| UE-J4 | Search Deeplink | Android | CONFIRMED | **CONFIRMED** (ubereats://search → LauncherActivity) | HIGH |
| UE-J5 | Deals Deeplink | Android | CONFIRMED | **CONFIRMED** (page loads at /mx/deals) | VERY HIGH |
| UE-J6 | Category Feed | Android | CONFIRMED | **PARTIAL** (307 redirect without session) | HIGH |
| UE-J9 | Membership | Android | CONFIRMED | **CONFIRMED** (page loads at /mx/membership) | MEDIUM |
| UE-J18 | Native Deeplink | Android | CONFIRMED | **CONFIRMED** (ubereats:// → LauncherActivity) | HIGH |
| UE-S1 | Sitemaps | Web | (new) | **CONFIRMED_CONTRACT** (74,328 MX stores) | **VERY HIGH** |
| UE-N1 | Near-me Discovery | Web | (new) | **CONFIRMED_CONTRACT** (~80 stores/category) | HIGH |
| UE-BR1 | Brand Pages | Web | (new) | **CONFIRMED_CONTRACT** (cached 24h) | MEDIUM |
| UE-LD1 | JSON-LD Schema.org | Web | (new) | **CONFIRMED_CONTRACT** (Restaurant, BreadcrumbList, FAQPage) | HIGH |

### Rejected / False Positives

| ID | Name | 5B.1 Status | 5B.2 Result | Reason |
|---|---|---|---|---|
| UE-B1 | __NEXT_DATA__ | CONFIRMED | **REJECTED** | Uber Eats uses Fusion.js, NOT Next.js |
| UE-J7 | Near-me SEO (`convenience-store`) | CONFIRMED | **REJECTED** (404) | Category slug not valid |
| UE-J8 | Food Delivery SEO | CONFIRMED | **REJECTED** (301→404) | Redirects to invalid path |
| — | `/sitemap.xml` (root) | N/A | **REJECTED** (404) | Sitemaps in robots.txt only |
| — | `/mx/city/*` | N/A | **REJECTED** (404) | Not a valid URL pattern |
| — | SSO Content Provider | N/A | **BLOCKED** | Signature-protected |
