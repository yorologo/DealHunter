# UBER EATS SURFACES INVENTORY

This document records the data surfaces discovered during Phase 5B recon.

## UE-A1: Web Discovery Feed (getFeedV1)
- **Status**: CONFIRMED_STATIC (via documentation & source analysis)
- **Path**: `https://www.ubereats.com/_p/api/getFeedV1`
- **Method**: POST
- **Auth Level**: SESSION_REQUIRED (or WAF token required)
- **Role**: Fetching the localized feed of available merchants.
- **Notes**: Blocked by `def.uber.com/challenge` WAF if accessed without a valid browser fingerprint.

## UE-C1: Web Store Catalog (getStoreV1)
- **Status**: CONFIRMED_STATIC
- **Path**: `https://www.ubereats.com/_p/api/getStoreV1`
- **Method**: POST
- **Auth Level**: SESSION_REQUIRED
- **Role**: Fetching the full menu and taxonomy of a specific merchant.
- **Notes**: Requires `storeUuid` (e.g., `vN5-d143RhyuKDBH7Oq4Kw`).

## UE-E1: Store UUID Format
- **Status**: CONFIRMED_DYNAMIC (via search engine indexing)
- **Format**: URL-safe base64 / UUID hybrid (e.g., `vN5-d143RhyuKDBH7Oq4Kw`).
- **Role**: Identifies the merchant uniquely.
- **Notes**: Completely incompatible with Rappi's integer IDs. Mandatory requirement for `UE-` namespacing in SQLite.

## UE-B1: Redux SSR State (`__REDUX_STATE__`)
- **Status**: CONFIRMED_DYNAMIC
- **Location**: Embedded in initial HTML shell.
- **Auth Level**: PUBLIC
- **Role**: Bootstraps the application state.
- **Notes**: Does not contain the catalog natively; it delegates to client-side hydration via `getFeedV1`.
