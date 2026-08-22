# Architecture

DealHunter sigue una arquitectura monolítica local orientada a servicios de dominio encapsulados, que pueden ser invocados tanto desde el CLI (`rappi-historico` / `rappi-ofertas`) como desde la Web UI.

```mermaid
flowchart TB
    UI[Web UI]
    CLI[CLI]

    UI --> SERVICES[Domain Services]
    CLI --> SERVICES

    SERVICES --> NORM[Normalization]
    SERVICES --> PI[Price Intelligence]
    SERVICES --> MATCH[Product Matching]
    SERVICES --> ALERTS[Alerts Engine]
    SERVICES --> ACCOUNT[Account Diagnostics]
    SERVICES --> DOCTOR[Doctor]

    SERVICES --> DB[(SQLite)]

    CRAWLER[Crawler / Providers] --> SERVICES
```

## Data Flow

```mermaid
flowchart LR
    PROVIDER[Rappi APIs]
    CRAWLER[Crawler]
    NORMALIZE[Normalization]
    DB[(SQLite)]
    PI[Price Intelligence]
    MATCH[Matching]
    ALERT[Alerts]
    CLI[CLI]
    WEB[Web UI]

    PROVIDER --> CRAWLER
    CRAWLER --> NORMALIZE
    NORMALIZE --> DB

    DB --> PI
    DB --> MATCH
    DB --> ALERT

    PI --> CLI
    MATCH --> CLI
    ALERT --> CLI

    PI --> WEB
    MATCH --> WEB
    ALERT --> WEB
```

Todos los servicios acceden a una misma base de datos `SQLite`, minimizando dependencias externas y permitiendo portabilidad.

### Crawler Architecture & Session Flow

DealHunter implements a dual-mode crawling strategy routed by the **Session Resolver** which determines the **Effective Session**:

```mermaid
flowchart TD
    CONFIG[Local Storage / Env] --> RESOLVER
    NETWORK[Rappi API] -. Validation .-> RESOLVER
    
    RESOLVER[Session Resolver] --> EFFECTIVE{Effective Session?}
    
    EFFECTIVE -- "VALID / CONFIGURED" --> ZONE[Zone Inventory]
    EFFECTIVE -- "EXPIRED / NOT_CONFIGURED" --> SEARCH[Search Discovery]

    ZONE -.->|401 Unauthorized| FALLBACK[Partial Run & Fallback]
    FALLBACK --> SEARCH

    ZONE --> CORE[Core Data Pipeline]
    SEARCH --> CORE

    subgraph Core
    CORE --> NORM[Normalization]
    NORM --> DB[(SQLite)]
    end
```

- **Session Resolver**: Unified single source of truth evaluating local session material (`SecretStore`) against network assertions.
- **Zone Inventory**: Uses authenticated endpoints to get full store catalogs in the active zone. Reconciles availability (STALE/UNAVAILABLE) *only* upon full completion.
- **Search Discovery**: Falls back to anonymous search queries to organically discover available deals. Does NOT perform destructive reconciliation.
- **Same Core**: Both crawlers utilize the exact same normalization, product mapping, filtering, and database ingestion core.
- **401 Fallback**: If a Zone Inventory run encounters an HTTP 401 mid-flight, the run is finalized as `PARTIAL` to prevent false deletion, and a new `SEARCH_DISCOVERY` run takes over automatically.
