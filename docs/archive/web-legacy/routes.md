# Web Routes

Este es el mapa de rutas Web operativas del RC v3.2.0.

| Route | Method | Purpose | Source / Network |
|---|---|---|---|
| `/` | GET | Dashboard de inicio | DB |
| `/deals` | GET | Listado de oportunidades | DB |
| `/market` | GET | Productos supermercado | DB |
| `/turbo` | GET | Productos Turbo | DB |
| `/restaurants` | GET | Lista de restaurantes | DB |
| `/restaurants/<provider>/<store_id>` | GET | Menú del restaurante | DB |
| `/categories` | GET | Resumen de categorías | DB |
| `/categories/<category>` | GET | Productos de la categoría | DB |
| `/products` | GET | Directorio de productos | DB |
| `/products/<provider>/<store_id>/<product_id>` | GET | Product Detail, historial, comparativas | DB |
| `/stores` | GET | Lista de tiendas | DB |
| `/stores/<provider>/<store_id>` | GET | Vista de tienda | DB |
| `/compare` | GET | Comparador global de productos | DB |
| `/watchlist` | GET | *Placeholder (Próximamente)* | - |
| `/alerts` | GET | *Placeholder (Próximamente)* | - |
| `/admin` | GET | Admin Home Dashboard | DB |
| `/admin/account` | GET | Account Diagnostics (Read-only) | Local env |
| `/admin/account/check` | POST | Explicit network diagnostic | Network |
| `/admin/runs` | GET | Lista de runs/ejecuciones | DB |
| `/admin/runs/<run_id>` | GET | Detalle de run | DB |
| `/admin/events` | GET | Eventos y errores estructurados | DB |
| `/admin/doctor` | GET | Doctor Diagnostics (Local only) | Local env/DB |
| `/admin/doctor/check` | POST | Doctor con red opt-in | Network |
| `/admin/database` | GET | Resumen y esquema de Base de Datos | DB |
| `/admin/database/backup` | POST | Crea un snapshot `.bak` | Disk |
| `/admin/database/integrity` | POST | Valida corrupción SQLite | DB |
| `/admin/settings` | GET | Panel de configuración (Read-only) | Config file |
| `/admin/settings/update` | POST | Modificación de setting (SAFE_EDITABLE) | Disk |
| `/api/open-rappi` | POST | Abre el `store_id` exacto en la app oficial mediante deep link nativo | Android/Shizuku |
| `/search` | GET | Búsqueda global | DB |
| `/best` | GET | Mejores ofertas por Deal Score | DB |

> Nota: Las rutas POST están protegidas contra CSRF obligatoriamente. Las rutas GET no realizan peticiones de red externas. `/api/open-rappi` resuelve nombre/tipo desde SQLite, construye únicamente el deep link `gbrappi://com.grability.rappi?store_type=…&store_id=…` y lo entrega mediante `rish` al paquete fijo `com.grability.rappi`. Shizuku debe estar activo y Termux autorizado. No acepta URL, nombre o comando del cliente; no tiene fallback a browser, website, Home ni búsqueda UI. Los tipos no demostrados fallan cerrados.
