# Database Schema

Current `CURRENT_SCHEMA_VERSION = 16`.

La fuente de verdad es `src/dealhunter/db.py`; este documento resume el
contrato actual y no reemplaza al DDL/migrations ejecutables.

DealHunter gestiona las migraciones automáticamente en el arranque para preservar idempotentemente el historial de `observations`.

## Migraciones Clave

- **v5 → v6**: `products.category` estructurado.
- **v6 → v7**: `products.has_toppings` y `category_source`.
- **v9 → v10**: facetas y memberships N:M.
- **v11 → v12**: canales de precio público/membresía.
- **v13 → v14**: `alert_events`.
- **v14 → v15**: identidad raw provider-aware.
- **v15 → v16**: infraestructura canónica; no activa escrituras automáticas.

## Tablas Principales
- `stores`: Comercios identificados por `(provider, store_id)`.
- `products`: Catálogo raw identificado por `(provider, store_id, product_id)`.
- `runs`: Sesiones de crawler y procedencia geográfica (`started_at`, `finished_at`, `lat`, `lng`, `radius`, `vertical`, `status`).
- `observations`: Serie temporal con unicidad `(run_id, provider, store_id, product_id)`.
- `alerts`: Historial de notificaciones disparadas.
- `alert_events`: Transiciones idempotentes provider-aware.
- `watchlist`: Productos marcados por el usuario.
- `product_families`, `canonical_products`, `product_external_identifiers`, `canonical_product_members`, `product_identity_decisions`: infraestructura canónica de v16. Su existencia no implica auto-canonicalización.
- `schema_version`: Tabla de configuración interna.

La respuesta a “¿con qué ubicación se capturó esta observación?” se obtiene enlazando `observations.run_id → runs.run_id`. La ubicación se guarda una vez por run, no duplicada en cada producto. Las filas migradas antiguas pueden tener procedencia nula y deben tratarse como evidencia insuficiente hasta poder atribuirlas por metadata/fingerprint; nunca se eliminan automáticamente.
