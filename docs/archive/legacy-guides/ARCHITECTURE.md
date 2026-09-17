# DealHunter Architecture

## High-Level Architecture
```mermaid
graph TD
    A[Providers: Rappi, Uber Eats] -->|Discovery & Sync| B(Provider-aware Persistence)
    B --> C[(SQLite v17)]
    C --> D[Query / Eligibility / Score]
    D --> E[Web / Alerts / Watchlist]
```

Current RC boundary:

- Rappi and Uber Eats acquisition are production-capable.
- Raw identity is `(provider, store_id, product_id)`.
- Provider selection and Rappi Pro/Uber One eligibility are production configuration.
- Schema v17 is current. Raw provider identity remains authoritative even when a reviewed merchant/location mapping exists.
- `Provider Listing → Merchant → Location` is written only through explicit reviewed mapping; ambiguous listings remain `UNRESOLVED`.
- Raw provider taxonomy/path is preserved in `product_memberships`; only explicit reviewed `browse_mappings` classify it into `browse_nodes`; unmapped evidence remains `UNCLASSIFIED`.
- Product canonical matching remains shadow/experimental and cannot write memberships automatically.

## Identity Side Pipeline (Shadow / Experimental)
```mermaid
graph TD
    A[Raw Products] --> B[Evidence Extraction]
    B --> C[Normalization]
    C --> D[Bounded Candidate Generation]
    D --> E[Identity Decisions / Rules]
    E --> F[Canonical Infrastructure]
    F -.- G([Production Activation Gated])
```

## Schema Evolution
```mermaid
graph LR
    V9(v9 Legacy) --> V11(v11 Taxonomy)
    V11 --> V12(v12 Commercial Model)
    V12 --> V14(v14 Alert Events)
    V14 --> V15(v15 Membership)
    V15 --> V16(v16 Product Canonical Infrastructure)
    V16 --> V17(v17 Commercial Identity + Browse Taxonomy)
```

## Authority boundaries

1. **Raw provider listing identity:** `(provider, store_id)` is never replaced.
2. **Merchant identity:** explicit reviewed mapping only.
3. **Location/outlet identity:** explicit reviewed mapping only and tied to a reviewed merchant.
4. **Browse classification:** explicit raw-taxonomy/path → browse-node mapping only.
5. **Product canonical identity:** separate shadow/experimental system; automatic canonicalization stays OFF.

Catalog ordering is also authoritative: Web exposes only sort modes implemented by the Query Layer. `savings` and `recent` use persisted price/timestamp evidence; unsupported catalog `opportunity` is not advertised.

## SQLite connection boundary

New Web paths should reuse `dealhunter.db.read_connection` / `write_connection` instead of opening ad-hoc SQLite handles. `read_connection` uses SQLite `mode=ro` for filesystem databases, so a read cannot silently create or mutate the DB; `write_connection` commits on success and rolls back on failure. Migration is progressive rather than a repository-wide refactor.

Read surfaces must distinguish an empty result from a storage/query failure. In particular, Watchlist propagates DB failures, while Admin Home and Catalog Sync surface a visible database error instead of reporting `{}` or `0` as if that were authoritative data.
