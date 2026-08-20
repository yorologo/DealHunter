# Database Schema

Current `CURRENT_SCHEMA_VERSION = 7`.

DealHunter gestiona las migraciones automáticamente en el arranque para preservar idempotentemente el historial de `observations`.

## Migraciones Clave

- **v5 → v6**: Se incorporó la columna `category` a la tabla `products`, adoptando taxonomías estructuradas del proveedor en lugar de deducciones.
- **v6 → v7**: Se incorporó `has_toppings` a `products`. 

## Tablas Principales
- `stores`: Listado de comercios y su tipo (market, turbo, restaurant).
- `products`: Catálogo central y normalización.
- `runs`: Sesiones de crawler y procedencia geográfica (`started_at`, `finished_at`, `lat`, `lng`, `radius`, `vertical`, `status`).
- `observations`: Serie temporal de precios por `run_id`.
- `alerts`: Historial de notificaciones disparadas.
- `watchlist`: Productos marcados por el usuario.
- `schema_version`: Tabla de configuración interna.

La respuesta a “¿con qué ubicación se capturó esta observación?” se obtiene enlazando `observations.run_id → runs.run_id`. La ubicación se guarda una vez por run, no duplicada en cada producto. Las filas migradas antiguas pueden tener procedencia nula y deben tratarse como evidencia insuficiente hasta poder atribuirlas por metadata/fingerprint; nunca se eliminan automáticamente.
