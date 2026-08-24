# Rappi Android API and call surfaces

## Scope

This document is the static-only inventory produced for Phase 4B.3D-A. Android is the primary source; the already documented Rappi Web observations are used only as a secondary naming oracle. No endpoint in this inventory was called, no direct API probe was made, no dynamic navigation was performed, and no database was read or modified for this phase.

Canonical repository baseline at the start of the phase:

- branch: `experiment/faceted-discovery-taxonomy`
- HEAD: `79cc94a2273d4dd8d34c732a6864841dc94f0c46`
- working tree: clean after preserving the unrelated temporary probe outside the repository

Static Android artifacts:

- package: `com.grability.rappi`
- APK version: `8.36.20260806-88868` (`versionCode=88868`, `targetSdkVersion=35`)
- `base.apk`: SHA256 `6ac1d446c651f05131f71bb7ddf9fc135de5b59aa4b473ae44f4a368d5a919d1`
- `libapp.so`: SHA256 `5eed56751cc7f50544b481a46dd12167609eee545017389cb8e674445478af36`

The methods below come from static Retrofit annotations in the DEX files. In the inspected build, `Lzx9/f` identifies GET, `Lzx9/o` POST, `Lzx9/p` PUT, and `Lzx9/h` an explicit HTTP method. Relative paths are recorded exactly as embedded; a leading slash is not normalized and a host is not invented when the APK only exposes a relative path.

`auth=UNKNOWN` is deliberate. An interface that does not declare an `Authorization` argument can still receive credentials from an OkHttp interceptor. Static request interfaces alone do not prove whether an anonymous call is accepted. The `read/write` column describes the apparent business effect, not merely the HTTP verb.

## Status and gap vocabulary

- `CONFIRMED_STATIC`: a literal annotated path/method or an explicit Android component/model proves the call or surface exists in this APK.
- `CANDIDATE`: the Android surface and useful model are explicit, but a dedicated transport path was not recovered.
- `UNCERTAIN`: a literal exists but its relevance to shopping discovery is weak or ambiguous.
- `ALREADY_USED`: DealHunter currently consumes the call or signal.
- `PARTIALLY_USED`: DealHunter consumes only a subset or an equivalent from another surface.
- `PRESENT_BUT_UNUSED`: explicit Android signal exists but DealHunter does not consume it.
- `POSSIBLE_OTHER_ANDROID_SURFACE`: likely useful Android surface whose transport or vertical role remains unresolved.
- `NEW_CANDIDATE`: concrete static candidate for a future controlled validation phase.

## Static source assessment

| Source | Result |
|---|---|
| Native DEX (`classes3`, `classes8`, `classes15`, `classes18`, `classes19`) | Primary evidence. Contains shopping Retrofit interfaces, Market/Search/Restaurant models, Prime models, product fields, navigation contracts, and server-driven home models. |
| `AndroidManifest.xml` | Confirms `MarketActivity`, search actions (`com.rappi.searchpage`, `.store`, `.product`), restaurant product/store detail actions, HTTPS app links, and the `gbrappi` scheme/hosts. |
| Android resources and Kotlin module metadata | Confirms packaged implementations for market product detail, aisles/subaisles, market offers, local/unified search, Prime, product suggestions, and store offers. |
| `libapp.so` | Mostly RappiPay/financial Flutter code. It does not expose the native Market/Search contracts listed below. The shopping-looking `/v3/orders/products?` string is retained only as low-confidence noise. |
| `flutter_assets` | Minimal RappiPay design-system assets, fonts, and shaders; no shopping catalog/taxonomy configuration found. |
| DealHunter source | Confirms actual use of unified search, selected product/promotion/stock fields, Web storefront catalogs, and the exact-store `gbrappi` URI. |

No static business GraphQL operation or shopping `query`/`mutation` document was confirmed. Generic GraphQL-related library strings, if any, are not treated as call evidence.

## Inventory summary

There are 41 actionable static inventory rows and 2 separately identified likely-noise rows. Of the 41, DealHunter already uses 2, partially uses 7, and does not use 32. Twelve unused rows are preliminarily `HIGH` value.

### A. Merchant discovery

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Unified merchant/product search | `/api/pns-global-search-api/v1/unified-search`; POST | Global Search | `classes8/wz8/a.smali`; `GlobalSearchUnifiedResponse` | UNKNOWN | READ | request `query`, `lat`, `lng`, `options`, `tiered_stores`, `size`; query flags `is_prime`, `unlimited_shipping`; response `filter_group`, `stores`, `metadata`, banners | YES | CONFIRMED_STATIC | HIGH | ALREADY_USED |
| A2 | Unified suggestions | `api/pns-global-search-api/v1/unified-suggestions`; POST | Search suggestions | `classes8/wz8/a.smali`, `classes8/k39/b.smali` | UNKNOWN | READ | query/edit-order request, suggestion response | NO | CONFIRMED_STATIC | MEDIUM | PRESENT_BUT_UNUSED |
| A3 | Recent/top searches | `api/pns-global-search-api/v1/unified-recent-top-searches`; POST; `api/cpgs/search/v1/recent-top-searches`; GET | Global and local search history/top terms | `classes18/ox0/b.smali`, `classes8/k39/b.smali` | UNKNOWN | READ | body context; `store_type`, `recent_limit`, `total_limit` | NO | CONFIRMED_STATIC | LOW | PRESENT_BUT_UNUSED |
| A4 | Search-client product search | `api/search-client/search/v2/products`; POST | Product search results | `classes8/k39/a.smali` | UNKNOWN | READ | `SearchBody`, `page`, raw product response | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| A5 | Context store enumeration | `api/dynamic/context/stores`; GET | Market/store discovery | `classes3/jr2/a.smali` | UNKNOWN | READ | `lat`, `lng`, `parent_store_type`, optional `shared_cart_token`; store JSON | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| A6 | Restaurant catalog search | `api/restaurant-bus/stores/catalog`; POST; `/api/restaurant-bus/stores/catalog/rests-search`; POST | Restaurant/coupon-eligible store discovery | `classes18/ng1/a.smali`, `classes18/i51/a.smali`; request `gg1/k` | UNKNOWN | READ | `latitude`, `longitude`, `store_type`, `store_ids`; response `stores`, `tags` | NO | CONFIRMED_STATIC | MEDIUM | POSSIBLE_OTHER_ANDROID_SURFACE |

Notes:

- DealHunter already calls A1 and reads `stores`, `store_id`, `store_name`, `parent_store_type`, `vertical_sub_group`, `categories`, `tags`, and embedded `products`; it does not consume the Android response's full filter, offer, store-status, delivery, or product-view model.
- A6 lives in a coupons/growth module and its response is store/tag oriented. Static evidence does not establish it as a full restaurant menu endpoint.

### B. Store metadata

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | Dynamic context resolver | `/api/dynamic/context/resolve`; POST | Direct server-driven context/store resolver | `classes3/zi2/a.smali` plus equivalent interfaces in DEX 8/18/19 | UNKNOWN | READ | request `context`, `stores`, `resolver`, `state`; response `component`; variants accept `city` and `prime_plan` | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| B2 | CPG store configuration | `/api/cpgs-orders/store-configuration/{storeId}`; GET | Market store setup | `classes3/jr2/b.smali`; `StoreConfigModel` | UNKNOWN | READ | `storeId`, `store_type`; `enable_reschedule`, `enable_modification`, `enable_low_stockout` | NO | CONFIRMED_STATIC | MEDIUM | NEW_CANDIDATE |
| B3 | Rich store metadata model | transport may be A1/A5/B1/M1 | Unified search and Market store cards/detail | `UnifiedStore`, `StoreModel`, `StoreDetailLite` | UNKNOWN | READ | IDs, name/type/parent type, vertical group/subgroup, status/open/availability, ETA, rating, delivery methods/cost, brand, offers, product count, deeplink, position | PARTIAL | CANDIDATE | MEDIUM | PARTIALLY_USED |
| B4 | Flat store zones | `api/dynamic/context/store-zones/flat`; GET | Dynamic context/store availability | `classes18/m51/d.smali` | UNKNOWN | READ | `lng`, `lat`, `retail_group`; flat store-zone list; `Accept-Version: 1` | NO | CONFIRMED_STATIC | LOW | POSSIBLE_OTHER_ANDROID_SURFACE |

### C. Store taxonomy and facets

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Guided search facets | `api/cpgs/search/v1/guided-search`; GET | CPG local search | `classes8/k39/b.smali` | UNKNOWN | READ | `searched_query`, `store_type`, `vertical`; guided-search response | NO | CONFIRMED_STATIC | MEDIUM | NEW_CANDIDATE |
| C2 | Quick-filter product counts | `api/cpgs/search/v1/store/{id}/product-count`; POST | CPG quick filters | `classes8/v39/a.smali`; `QuickFilterProductCountResponse` | UNKNOWN | READ | store ID, `lat`, `lng`, `city`, `user_id`, filter body, `total_products` | NO | CONFIRMED_STATIC | MEDIUM | NEW_CANDIDATE |
| C3 | Aisles/subaisles/category navigation | dedicated transport path not recovered | Market landing, aisle detail, subaisles | `SubAislesArgsModel`, `AislesDetailArgsModel`, `StoreCategoryIndexArgsModel`, `ProductCategory*ArgsModel`; resources/modules | UNKNOWN | READ | `store_id`, `aisles_id`, `store_type`, `parent_store_type`, `is_offer_context`, state/context; `aisle_id`, `vertical_aisle_id`, `main_category`, aisle images/type | PARTIAL | CANDIDATE | HIGH | PARTIALLY_USED |
| C4 | Category restriction context | `/api/dynamic/context/validate-user-identity`; POST; `/api/dynamic/context/modal-restriction`; GET | Age/identity restriction, not taxonomy enumeration | `classes19/zx1/a.smali`, `zx1/b.smali` | UNKNOWN | READ/UNKNOWN | `store_type`, `sub_vertical`, `category_id`, restriction headers/body | NO | CONFIRMED_STATIC | LOW | POSSIBLE_OTHER_ANDROID_SURFACE |

The exact Web wrapper name `aisles_tree_response` was not found in Android. Android nevertheless has explicit aisle/subaisle components and IDs, so the taxonomy surface is demonstrated even though its transport may be delivered by dynamic/home content.

### D. Product catalog

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | CPG store products v2 | `api/cpgs/search/v2/store/{id}/products` and `/api/cpgs/search/v2/store/{store_id}/products`; POST | Store-scoped Market catalog/search | `classes8/k39/b.smali`, `classes8/v39/a.smali` | UNKNOWN | READ | store ID, body, `lat`, `lng`, `city`, `user_id`; static headers `platform: android`, `browser: native`; product JSON | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| D2 | Dynamic-URL local product search | runtime URL; POST | Local search pagination | `classes8/k39/b.smali` method with `@Url`, `SearchBody`, `page` | UNKNOWN | READ | dynamic URL, search body, page | NO | UNCERTAIN | MEDIUM | POSSIBLE_OTHER_ANDROID_SURFACE |
| D3 | Restaurant menu/dish catalog surface | dedicated menu path not recovered | Restaurant store detail/menu | `Dish`, `Corridor`, `RestaurantProduct`, `StoreDetailLite`; restaurant dynamic-list modules | UNKNOWN | READ | dish/product ID, name, description, price/real price, corridor ID/name/index, toppings, schedules/status, discount, store data | NO | CANDIDATE | HIGH | POSSIBLE_OTHER_ANDROID_SURFACE |
| D4 | Restaurant banner products/stores | `/api/restaurant-bus/products/banners/{id_banner}/v2`; POST; `/api/restaurant-bus/stores/banners/v2`; POST | Banner-driven catalog/store lists | `classes8/fn8/a.smali` | UNKNOWN | READ | banner ID/body, products or stores | NO | CONFIRMED_STATIC | LOW | PRESENT_BUT_UNUSED |

DealHunter currently obtains full CPG and restaurant catalogs from documented Web storefront SSR fallbacks. It does not call D1-D4.

### E. Product taxonomy

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | Search product taxonomy | carried by A1/A4/D1 | Unified search/product results | `UnifiedProduct` | UNKNOWN | READ | `category_id`, `corridor_id`, `corridor_name`, `corridor_index`, product/store/master IDs | PARTIAL | CONFIRMED_STATIC | HIGH | PARTIALLY_USED |
| E2 | Market product/detail taxonomy | carried by catalog/detail/dynamic content | Market catalog and product detail | `Product`, `ProductInformation`, `ProductDetailBundle`, `CorridorAnalytic`, `SubCorridorAnalytic` | UNKNOWN | READ | `category_id`, `category_name`, `category`, corridor and subcorridor objects | PARTIAL | CONFIRMED_STATIC | HIGH | PARTIALLY_USED |

Android explicitly proves category and corridor identifiers. A literal generic `subcategory_id` was not confirmed; the strongest equivalent is the explicit `subCorridor` model. Therefore “subcategory ID” remains `UNKNOWN` as an exact Android field name.

### F. Product detail

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | Market product detail | transport path UNKNOWN | Market product detail screen | `ProductDetailBundle`; `market-product-detail-api/impl` modules; `fragment_product_detail.xml` | UNKNOWN | READ | product ID/name/image/description/sell data, category/corridor/subcorridor, offers, discount, master product ID, stockout product ID, filters, sponsored/source flags | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| F2 | Product detail across stores | transport path UNKNOWN | Product view/buy-box/store comparison | `ProductViewDetailStores`, `ProductViewUnifiedStore` | UNKNOWN | READ | master/product/store IDs, store/brand, price/real price, `pum`, stock/availability, discounts bundle, number/list of stores, vertical/subvertical, delivery/rating | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| F3 | Restaurant product detail resolver | `/api/restaurant-bus/deep-link/brand/{brandId}/store/{storeId}/product/{productId}`; GET | Restaurant deep-link/product-detail navigation | `classes8/kl8/a.smali`; manifest action `com.rappi.restaurants.product_detail` | UNKNOWN | READ | brand/store/product IDs; resolved navigation response | NO | CONFIRMED_STATIC | MEDIUM | POSSIBLE_OTHER_ANDROID_SURFACE |

The product-detail **surface** is confirmed. A dedicated Market product-detail HTTP endpoint is not statically demonstrated and must remain `UNKNOWN`.

### G. Promotions and NxM

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 | Product bundle/NxM metadata | carried by product/catalog responses | Market product cards/detail | `Product`, `BundleDiscounts`, `StepDiscount` | UNKNOWN | READ | exact `discounts_bundle`: `progressive`, `deal`, `percentage_all`, `percentage_unit`, `bundle`; step `type`, `promotion_value`, `units_condition`, `label`, `price`, `pum`, `id`, `max_bundles` | PARTIAL | CONFIRMED_STATIC | HIGH | PARTIALLY_USED |
| G2 | Direct and membership discount metadata | carried by product/catalog responses | Market product cards/detail | `Discount`, `PrimeDiscount`, `Offer` | UNKNOWN | READ | `earnings`, `pay_products`, `discount`, `type`, `tag_color`, exact `prime`; `price_with_discount`; offer type/condition/text/value/max quantity/ID | NO | CONFIRMED_STATIC | HIGH | PRESENT_BUT_UNUSED |
| G3 | Coupon discovery/evaluation | `/api/discounts-proxy/coupons`; POST; `api/ms/coupon-root/coupons/enabled`; GET; Prime coupon evaluate POST | Account/promotion eligibility | `classes18/ng1/a.smali` | UNKNOWN | READ | status/include-enabled, lat/lng, coupon offer/store/product context | NO | CONFIRMED_STATIC | MEDIUM | PRESENT_BUT_UNUSED |
| G4 | Payment-method discounts | `api/ms/payment-method/discounts`; GET | Checkout/payment eligibility, not product price | `classes18/tv0/b.smali` | UNKNOWN | READ | `store_type`, `origin`, `store_id` and discount response | NO | CONFIRMED_STATIC | LOW | PRESENT_BUT_UNUSED |

G3/G4 may describe user eligibility rather than a generally available product deal. They must not be combined with product discount math without later validation.

### H. Pro and Prime

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | Prime plans and status | `api/ms/rappi-prime/plans`; GET; `api/ms/rappi-prime/prime-status`; GET | Prime membership context | `classes18/dl1/e.smali` | UNKNOWN | READ | available plans, subscription/status | NO | CONFIRMED_STATIC | MEDIUM | PRESENT_BUT_UNUSED |
| H2 | Prime/Pro exclusive products | `api/ms/discounts-availability/exclusive-products`; GET | Prime exclusive products/deals | `classes18/dl1/e.smali` | UNKNOWN | READ | `lat`, `lng`, `size`, `page`, `discount_from`, `discount_to`; exclusive product response | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| H3 | Prime widgets and hubs | `api/ms/rappi-prime/widget/{source}` and generic widgets; POST; `widget/exclusive`, partners, modal; GET; `widget/screen/discounts_hub` and `principal_hub`; POST | Prime UI/server-driven benefits | `classes18/dl1/e.smali`; Prime resources | UNKNOWN | READ | source/maps, generic widget, exclusive/partner/benefit content | NO | CONFIRMED_STATIC | LOW | PRESENT_BUT_UNUSED |
| H4 | Prime subscription mutations | `subscription/subscribe`, `activate`, `cancel`, `change_plan`, payment-method change and related paths; POST/PUT | Account subscription management | `classes18/dl1/e.smali` | UNKNOWN | WRITE | plan/payment/subscription state | NO | CONFIRMED_STATIC | LOW | PRESENT_BUT_UNUSED |

H4 is documented solely to mark the write boundary. It is outside DealHunter's read-only mission and must not be validated.

### I. Stock and availability

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I1 | Product stock/availability signals | carried by search/catalog/detail responses | Product cards, search, product view | `Product`, `UnifiedProduct`, `ProductViewDetailStores` | UNKNOWN | READ | `in_stock`, `stock`, `is_available`, `available`, `possibly_out_of_stock`, `is_possible_stockout`, `is_discontinued` | PARTIAL | CONFIRMED_STATIC | HIGH | PARTIALLY_USED |
| I2 | Cart stockout resolver | `/api/cpgs-cart/stockout`; POST | Low-stock/stockout substitution | `classes3/zi2/a.smali`; `cj2/e`, `cj2/g` | UNKNOWN | UNKNOWN | request products; response `stockout_products`, preferred/suggested product signals | NO | CONFIRMED_STATIC | MEDIUM | NEW_CANDIDATE |

I2 may be a read-like availability calculation, but its business side effects are not proven statically; it remains `UNKNOWN` and should not be called in this phase.

### J. Collections and offers

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| J1 | Store-type product offers | `/product-offers/{storeType}`; GET | Market Offers | `classes3/vt2/a.smali`; module `market-offers-impl` | UNKNOWN | READ | `storeType`; raw offer/product JSON | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| J2 | Global offers/offer collections | transport likely dynamic/home content; exact path UNKNOWN | `store_offers_home`, offers world/detail, global-offer cards, aisle collections | `GlobalOfferResponse`, `DiscountResponse`, `OfferResponse`; `fragment_store_offers_home_context.xml`; `AislesListCollection` | UNKNOWN | READ | discounts/offers; offer ID/type/tag/value/title/description/URL/min amount/priority/Prime-exclusive/card details; aisle icons/has-more | NO | CANDIDATE | HIGH | NEW_CANDIDATE |

An exact Android payload field named like the Web `collections` node was not proven. Android does prove structured offer and aisle-collection surfaces; the equivalence to Web `collections` remains a candidate, not a confirmed mapping.

### K. Navigation and deeplinks

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| K1 | Structured response navigation | carried by product/dynamic responses | Product cards, highlighted categories, dynamic content | `NavigationResponse`, highlight `DeepLink`, multiple dynamic-list navigation models | UNKNOWN | READ | exact `navigation.deeplink`, `navigation.fallback`; `market_type`, `store_type`, `corridor_id` | PARTIAL | CONFIRMED_STATIC | HIGH | PARTIALLY_USED |
| K2 | Android intent/deep-link contracts | `gbrappi://com.grability.rappi?...`; HTTPS app links; internal actions | App entry, exact store, search/product/store detail | `AndroidManifest.xml`; DealHunter `web/rappi_native.py` | NO | READ/navigation | `store_type`, `store_id`; search store/product actions; restaurant product/store detail actions | YES | CONFIRMED_STATIC | MEDIUM | ALREADY_USED |

DealHunter constructs the verified exact-store K2 URI, but does not consume K1's provider-supplied `navigation.deeplink`/`fallback` objects.

### L. Recommendations

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L1 | CPG cross-selling by keyword | `api/cpgs/search/v1/cross-selling-products/by-keyword`; POST | Local search complementary products | `classes8/k39/b.smali`; `CrossSellingResponse` | UNKNOWN | READ | search body, `cross_selling_products` | NO | CONFIRMED_STATIC | MEDIUM | NEW_CANDIDATE |
| L2 | Restaurant checkout recommendations | `/api/restaurant-bus/products/checkout-recommendations`; POST | Restaurant product recommendations | `classes8/kl8/a.smali`; `ll8/g`, `ll8/h` | UNKNOWN | READ | `product_ids`, recommended `products` | NO | CONFIRMED_STATIC | MEDIUM | POSSIBLE_OTHER_ANDROID_SURFACE |

### M. Other server-driven/read surfaces

| ID | Logical call/surface | Path or pattern; method | Probable Android surface | Static source | Auth | Read/write | Useful associated fields | DealHunter uses | State | Utility | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | Home Router content | `api/home-router/context/content`; POST; `.../more-items`; POST; `api/home-router/content/metadata`; GET; `api/home-router/tab-bar`; GET | Server-driven home, collections, navigation | `classes19/jn1/a.smali`, `classes15/ln0/e.smali`, equivalent interfaces | UNKNOWN | READ | body context; `city`, `prime_plan`, `Accept-Version`, `shared_cart_token`; metadata `context`, `lat`, `lng`, `city_id`, `prime`, `prime_membership` | NO | CONFIRMED_STATIC | HIGH | NEW_CANDIDATE |
| M2 | Core Home Builder | `api/ms/core-home-builder/build`; POST | Older/parallel home composition | `classes18/wr0/a.smali` | UNKNOWN | READ | body, `lat`, `lng`, `view`; built components | NO | CONFIRMED_STATIC | MEDIUM | NEW_CANDIDATE |

## Likely noise, kept separate

| Logical string | Static evidence | Reason not counted as an actionable candidate |
|---|---|---|
| `/v3/orders/products?` | `libapp.so`/Flutter AOT | Located inside a predominantly RappiPay/financial Flutter module. Associated fields look like card/order products, not native Market catalog discovery. `UNCERTAIN`, `LOW`. |
| `v1/merchants/` | payment/Wompi DEX module | Refers to payment merchant/pre-acceptance behavior, not Rappi shopping merchant discovery. `UNCERTAIN`, `LOW`. |

## Android fields of highest DealHunter relevance

The common native `Product` model statically serializes all of the following in one commercial object:

- identity: `id`, `product_id`, `master_product_id`, `ean`, `retail_id`, `store_id`, `store_type`
- price/unit: `price`, `real_price`, `balance_price`, `real_balance_price`, `unit_price`, `real_unit_price`, `pum`, quantity/unit/sale-type fields
- taxonomy: `category_id`, `category_name`, `category`
- promotions: `discounts`, `discounts_bundle`, `offers`, `has_global_offers`, `global_offer_max_quantity`, discount earnings/pay-products/type/label/color
- availability: `in_stock`, `stock`, `is_available`, `available`, possible-stockout and discontinued flags
- navigation: `navigation` containing `deeplink` and `fallback`
- product/detail context: description, provider, toppings, rules, labels, metadata, analytics, sponsored/ad data

DealHunter currently uses product identity/name/store, base and reference price, stock/availability, category name, toppings, trademark/image, direct discount, and the first NxM `deal` step. It does not use `pum`, `master_product_id`, `ean`, `category_id`, offer lists, Prime discount detail, other bundle families, provider navigation, rules/labels, or product-view cross-store data.

## Web checklist mapped to Android

This checklist uses only the findings already recorded in `docs/RAPPI_WEB_ORACLE.md`; no new Web request was made.

| Existing Web observation | Android static equivalent | Result |
|---|---|---|
| `aisles_tree_response` | Aisle/subaisle modules and arguments; `aisle_id`, `vertical_aisle_id`, `main_category`, aisle icons/type, `AislesListCollection` | Equivalent surface: YES. Exact Web wrapper name in Android: UNKNOWN. |
| `corridors` | `UnifiedProduct.corridorId/corridorName/corridorIndex`; restaurant `Dish` equivalents; `ProductDetailBundle.corridor/subCorridor` | YES. |
| category/subcategory IDs | exact `category_id` in `Product`, `ProductInformation`, and `UnifiedProduct`; `corridor_id`; explicit `subCorridor` object | Category/corridor: YES. Exact generic `subcategory_id`: UNKNOWN. |
| `discounts.prime` | `Discount` serializes exact `prime` into `PrimeDiscount(price_with_discount, discount)` | YES. |
| `discounts_bundle` | exact field in `Product`; `BundleDiscounts` and `StepDiscount` expose all major bundle shapes and NxM values | YES. |
| promotion metadata | `Offer`, `Discount`, `StepDiscount`, global `OfferResponse`; IDs/types/conditions/values/labels/limits/priority/Pro exclusivity | YES. |
| `pum` | exact `pum` in `Product`, `UnifiedProduct`, `ProductViewDetailStores`, and discount steps | YES. |
| `stock` | exact `stock`, `in_stock`, availability and stockout flags across product models | YES. |
| `navigation.deeplink` | exact `NavigationResponse(deeplink, fallback)` plus manifest `gbrappi` contracts | YES. |
| `collections` | structured aisle collections, global offers, store offers home, server-driven home content | Probable equivalent: YES; exact payload mapping/path: UNKNOWN. |

## DealHunter gap assessment

### Already used

- A1 unified search for merchant/product discovery.
- K2 exact-store `gbrappi` navigation with verified store type and ID.

### Partially used

- B3 only a small subset of the rich Android store metadata is normalized.
- C3/E1/E2 taxonomy names and Web-derived memberships are used, but Android aisle/category/corridor IDs are not systematically retained from these surfaces.
- G1 only the first `discounts_bundle.deal` step and its NxM values/label are used; progressive, percentage, bundle, PUM, limit and exclusivity metadata are unused.
- I1 `in_stock`, `is_available`, and `stock` are used; alternate availability, possible-stockout and discontinued signals are not.
- K1 provider-supplied structured navigation is not consumed; DealHunter constructs only the known store URI.

### Present but unused

- `pum`, `master_product_id`, `ean`, `category_id`, corridor IDs/indexes.
- direct `Discount.prime`/`PrimeDiscount`, other bundle families, offers/global offers, offer limits and Pro-exclusive flags.
- rich store status/ETA/rating/delivery/brand/offers metadata.
- Prime plans/status/widgets, coupon and payment-eligibility signals.
- search suggestions/recent terms and banner-driven product/store lists.

### Possible other Android surfaces

- dynamic/home content as the transport for aisles, collections, product detail, and store offers.
- restaurant menu/detail models whose dedicated menu transport path was not recovered.
- dynamic-URL local product search.
- category restriction and store-zone context.
- Turbo/chiper specialization beyond shared CPG endpoints.

### New candidates

- D1 store-scoped CPG products.
- A5 direct context store enumeration and B1 context resolve.
- J1 store-type product offers.
- H2 exclusive products with discount bounds.
- C1/C2 guided search and quick-filter counts.
- F1/F2 Market product detail and cross-store product view.
- M1 home-router content and metadata.
- L1 CPG cross-selling.

## Key questions answered from static evidence only

| Question | Answer | Evidence boundary |
|---|---|---|
| Does a product-detail endpoint/surface appear to exist? | YES, the Market and Restaurant product-detail surfaces exist. The dedicated Market endpoint path is UNKNOWN. | Product-detail modules/resources/models, product-detail manifest action, restaurant deep-link resolver. |
| Does taxonomy/aisle/category appear to exist? | YES. | Aisle/subaisle/category modules and IDs; category/corridor fields and models. |
| Do offers appear to exist? | YES. | Confirmed GET `/product-offers/{storeType}`, Market Offers module, global/store offer models and screens. |
| Does Pro/Prime appear to exist? | YES. | Prime status/plans/exclusive-products/widget endpoints; `discounts.prime`; `is_pro_exclusive` with `is_prime_exclusive` alias. |
| Does stock/inventory appear to exist? | YES. | Product stock/availability fields and `/api/cpgs-cart/stockout`. A standalone inventory endpoint was not found. |
| Does a direct store resolver appear to exist? | YES. | POST `/api/dynamic/context/resolve`; GET `api/dynamic/context/stores`. Exact semantics of every resolver variant remain unvalidated. |
| Does a Turbo/chiper-specific surface appear to exist? | YES at the surface/type level; a dedicated Turbo-only catalog endpoint is UNKNOWN. | `chiper_home`, `turbo_home`, `cpgs_home_header_turbo_v2`, Turbo enums/tags/resources and Turbo navigation classes. |
| Do structured deeplinks appear to exist? | YES. | `NavigationResponse(deeplink, fallback)`, highlight `DeepLink`, manifest `gbrappi` and HTTPS links, restaurant resolver. |

## Preliminary validation priority for a later phase

No validation was performed here. If a separately authorized read-only validation phase follows, the static evidence suggests this order:

1. D1 CPG store products v2: highest direct catalog-coverage value.
2. A5 context stores: direct merchant enumeration without search saturation.
3. B1 context resolve: direct store/context resolver candidate.
4. J1 product offers by store type: explicit offers surface.
5. C1/C2 guided search and quick-filter counts: facet semantics and bounded discovery.
6. H2 exclusive products: Prime/Pro deal coverage, with account/auth isolation.
7. F1/F2: first recover the actual transport path; do not guess a product-detail URL.
8. M1 home-router: likely carrier for collections/aisles/offers, but server-driven and potentially noisy.
9. D3/F3 restaurant surfaces: distinguish menu transport from navigation and coupon catalog.
10. L1/L2 recommendations: useful only after core catalog/detail coverage is understood.

Likely noise or low priority: Flutter `/v3/orders/products?`, payment `v1/merchants/`, recent-search history, banner surfaces, payment-method discounts, Prime subscription writes, and category-restriction UI calls.

## Phase 4B.3D-B1 Validation Results

**D1: POST api/cpgs/search/v2/store/{store_id}/products**
- **Validation Status**: NEEDS_MORE_CONTRACT_INFO / CONFIRMED_LOW_VALUE
- **Actual Request Behavior**: Requires a non-empty `query` and `size` parameter. Empty queries return HTTP 400 "Keyword Empty". Wildcards like `*` return empty product arrays. 
- **Fields Observed**: N/A (requires valid keyword to return items).
- **Usefulness**: Very low for DealHunter's ingestion. It cannot dump a full catalog, acting strictly as an in-store text search.
- **Limitations**: Impossible to perform a 1-request full catalog sweep.
- **Recommended Role**: Ignore for Inventory mode. Web SSR (`catalog_sync.py`) remains the vastly superior oracle for dumping CPG catalogs.

**A5: GET api/dynamic/context/stores**
- **Validation Status**: NEEDS_MORE_CONTRACT_INFO
- **Actual Request Behavior**: HTTP 400 with `Invalid Parameters : [language]`.
- **Fields Observed**: N/A
- **Usefulness**: Unknown until the precise Android headers or query string parameters (language, country, app version) are reverse-engineered.
- **Limitations**: Cannot be invoked safely without guessing parameters.
- **Recommended Role**: Pending deeper reverse engineering (APK inspection).

**B1: POST /api/dynamic/context/resolve**
- **Validation Status**: NEEDS_MORE_CONTRACT_INFO
- **Actual Request Behavior**: HTTP 500 Internal Server Error with payload `{"lat": lat, "lng": lng, "store_id": "..."}`.
- **Fields Observed**: N/A
- **Usefulness**: Unknown.
- **Limitations**: The exact JSON contract is complex and requires undocumented fields (likely context vectors or device descriptors).
- **Recommended Role**: Stick to Web fallback or `unified-search` for store resolution until contract is proven.
