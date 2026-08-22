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

### Crawler Fallback Architecture

DealHunter dynamically chooses its strategy based on the availability of a valid session:

```mermaid
flowchart TD
    START[Crawler Run]
    SESSION{Sesión válida?}

    START --> SESSION

    SESSION -- Sí --> ZONE[Zone Inventory]
    SESSION -- No --> SEARCH[Search Discovery]

    ZONE --> CORE[Normalization + SQLite]
    SEARCH --> CORE

    CORE --> PI[Price Intelligence]
    CORE --> ALERTS[Alerts]
```

- **SESSION VALID -> Zone Inventory**: Uses authenticated endpoints to get full store catalogs in the active zone.
- **SESSION UNAVAILABLE -> Search Discovery**: Falls back to anonymous search queries to discover available deals.
