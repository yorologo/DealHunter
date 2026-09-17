# Modelo de Base de Datos SQLite

La versión actual utiliza la DB local `rappi-deals.db`, schema v16, estructurada
relacionalmente bajo la idea de "entidad estable" frente a "evento temporal".
El DDL en `src/dealhunter/db.py` es la fuente de verdad.

## Esquema Físico (Tablas)

### 1. `runs`
Contiene la telemetría de la sesión del scraper.
* `run_id` (TEXT PRIMARY KEY)
* `started_at` (DATETIME)
* `finished_at` (DATETIME)
* `lat` (REAL)
* `lng` (REAL)
* `radius` (REAL)
* `vertical` (TEXT)
* `status` (TEXT)

### 2. `stores`
Catálogo de entidades de comercio extraídos.
* `provider` (TEXT)
* `store_id` (TEXT)
* `name` (TEXT)
* `brand` (TEXT)
* `type` (TEXT)
* `PRIMARY KEY (provider, store_id)`

### 3. `products`
Catálogo físico de bienes y servicios (Identificador estable y deduplicado).
* `product_id` (TEXT)
* `store_id` (TEXT)
* `provider` (TEXT)
* `name` (TEXT)
* `brand` (TEXT)
* `image` (TEXT)
* `PRIMARY KEY (provider, store_id, product_id)`

### 4. `observations`
Tabla append-only para seguimiento histórico de precio real. Vincula el producto físico en el tiempo con la ejecución activa.
* `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
* `run_id` (TEXT) - FK simbólico a runs.
* `provider` (TEXT)
* `store_id` (TEXT)
* `product_id` (TEXT)
* `price` (REAL)
* `original_price` (REAL)
* `stock` (INTEGER)
* `timestamp` (DATETIME)
* `discount_effective` (REAL)
* `discount_source` (TEXT)
* `promotion_type` (TEXT)
* `promotion_label` (TEXT)
* `UNIQUE (run_id, provider, store_id, product_id)` - Deduplica una oferta raw dentro de un run.

### 5. Infraestructura canónica v16

* `product_families`
* `canonical_products`
* `product_external_identifiers`
* `canonical_product_members`
* `product_identity_decisions`

Estas tablas añaden una capa sobre los IDs raw. El matcher sigue en shadow y
no existe un path automático que escriba memberships canónicas.

## Migración histórica v2
La DB originalmente ligaba el producto con su precio fijo de manera destructiva. La refactorización renombró observaciones, protegió las viejas mediante `run_legacy_v1` e impuso el constraint `UNIQUE` que permite un crecimiento de datos saludable limitando escrituras innecesarias.
