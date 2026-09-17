# Web UI

DealHunter usa una capa Web deliberadamente delgada:

```text
Browser → Flask/Jinja/HTMX → query/domain services → SQLite
```

- Flask + Jinja2 para SSR.
- HTMX para interacciones parciales.
- Bootstrap 5 y Chart.js vendorizados; no hay CDN en runtime.
- SQLite y servicios de dominio siguen siendo la autoridad; la Web no reimplementa Price Intelligence, matching, alertas ni configuración efectiva.

## Navegación

La interfaz agrupa las funciones en cuatro áreas:

- **Comprar**: oportunidades, supermercados, Turbo, restaurantes y categorías.
- **Investigar**: productos, tiendas, detalle, histórico, búsqueda y comparación.
- **Seguir**: Watchlist y Alertas de sólo lectura sobre los motores existentes.
- **Administrar**: cuenta, runs/eventos, Doctor, DB/backup, Settings y Catalog Sync.

El mapa exacto de rutas es código (`src/dealhunter/web/routes.py` y `admin.py`), no una tabla duplicada que deba sincronizarse manualmente con cada cambio.

## Límites de seguridad

- La Web escucha por defecto sólo en `127.0.0.1`.
- GET de navegación no debe ejecutar adquisición remota ni mutar estado.
- Acciones mutables usan POST + CSRF.
- Secrets nunca se renderizan; la UI sólo muestra estado/configuración segura.
- Account/Doctor de red requieren acción explícita.
- Backup/integrity usan funciones internas; no existe SQL arbitrario en la UI.
- `/api/open-rappi` construye únicamente deep links soportados desde IDs/tipos resueltos en SQLite y falla cerrado si Shizuku/Intent/tipo no son válidos.

## Catalog Sync

Con sesión Rappi válida se usa Zone Inventory. Sin sesión o con sesión no válida, Search Discovery mantiene cobertura limitada sin reconciliación destructiva. Un fallo parcial no convierte ausencias no observadas en bajas definitivas.

El scheduler se administra desde la UI o `dealhunter scheduler`; la política operativa canónica está en `operations.md`.
