# Rappi Web Oracle Strategy

## Architecture & Principles
1. **Primary Source**: Rappi Android API (via Termux/DealHunter core). 
2. **Secondary Source**: `rappi.com.mx` public web.
3. **Evidence Rule**: Web provides structural enrichment and taxonomy validation but MUST NOT silently overwrite valid Android payloads. 
4. **Resilience**: If Web changes structure, goes down, or requires CAPTCHAs, DealHunter Android crawler continues unhindered.
5. **No Bypasses**: Bypassing Cloudflare/WAF or solving CAPTCHAs is explicitly out of scope. If the Web front door is locked, fall back to Android-only.

## Observed State (Phase 4B.3A)
* **Framework**: Next.js (SSR with JSON state bootstrapping).
* **Injection Vector**: `<script id="__NEXT_DATA__" type="application/json">`
* **Network Cost**: 1 public HTTP request yields an entire storefront taxonomy and partial/full product JSON. 
* **Auth Requirement**: 0. The storefront `__NEXT_DATA__` is publicly accessible without login/tokens for standard catalogs.

## Taxonomy Mapping

### Restaurants (e.g., Sushi Central)
* **Web Structure**: `fallback -> [key] -> corridors`
* **Android Mapping**: `corridors` exactly match the `product_memberships.raw_name` strings seen in Android.
* **Confidence**: **STRONG CATEGORY**. If an unknown membership string matches a web `corridor`, it is definitively a category/menu section.

### Supermarkets / Turbo / CPG (e.g., City Market)
* **Web Structure**: `fallback -> storefront/... -> aisles_tree_response.data.components`
* **Android Mapping**: `resource.name` perfectly aligns with Android container names. 
* **Confidence**: **STRONG CATEGORY**. `aisles` map to `CATEGORY`, solving the Android ambiguity between promotional widgets and actual inventory aisles.

## Commercial Metadata (Products)
The embedded JSON exposes highly valuable commercial metrics that complement Android:
* `pum` (Precio por Unidad de Medida)
* `stock`
* `discounts_bundle` (clear structural split for NxM, percentage, deal, and Pro)
* `navigation.deeplink` (direct Android fallback URI).

## Tooling & Integration Roadmap
1. **Semantic Taxonomy Reducer**: Automatically query Web `__NEXT_DATA__` to confidently reduce `UNKNOWN` memberships to `CATEGORY` or `COLLECTION`.
2. **Targeted Resolution Fallback**: When Android `discover_targeted()` fails (e.g., stale ID like Turbo 1930266218), querying Web resolves the active canonical SLUG/ID instantly.
