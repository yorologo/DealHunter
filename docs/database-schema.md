# Database Schema

Current `CURRENT_SCHEMA_VERSION = 7`.

DealHunter gestiona las migraciones automáticamente en el arranque para preservar idempotentemente el historial de `observations`.

## Migraciones Clave

- **v5 → v6**: Se incorporó la columna `category` a la tabla `products`, adoptando taxonomías estructuradas del proveedor en lugar de deducciones.
- **v6 → v7**: Se incorporó `has_toppings` a `products`. 

## Tablas Principales
- `stores`: Listado de comercios y su tipo (market, turbo, restaurant).
- `products`: Catálogo central y normalización.
- `runs`: Sesiones de Crawler.
- `observations`: Serie temporal de precios por `run_id`.
- `alerts`: Historial de notificaciones disparadas.
- `watchlist`: Productos marcados por el usuario.
- `schema_version`: Tabla de configuración interna.
