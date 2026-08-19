# Auditoría Inicial - Pre v2.1 Refactor

## Comandos y Flags Actuales
- `rappi-ofertas`: 
  - `--vertical`: String (default "general", choices: supermercado, farmacia, mascotas, bebe, higiene, hogar, tecnologia, test_run, general)
  - `--lat`: Float (default 19.4326)
  - `--lng`: Float (default -99.1332)
  - `--test`: Flag para ejecutar el vertical test_run
- `rappi-historico`:
  - `--min-history-days`: Float (default 1.0)
  - `--store`: String (ID de tienda)
  - `--product`: String (ID de producto)
  - `--json`: Output json a archivo y deshabilita tabla en stdout
  - `--top`: Int (default 50)

## Estructura de Módulos
- El código no está modularizado, consiste en scripts monolíticos en `bin/rappi-ofertas` y `bin/rappi-historico`. 
- Base de datos SQLite se busca en `DB_PATH` que puede provenir de `RAPPI_DB_PATH` o por defecto `~/rappi-deal-hunter/rappi-deals.db`.

## Configuración Actual
- No existe archivo de configuración persistente ni perfiles.
- La latitud y longitud por defecto están hardcodeadas en `rappi-ofertas`.
- Diccionario `VERTICALS` hardcodeado en `rappi-ofertas`.

## Esquema SQLite
Se infieren las siguientes tablas:
- `stores` (store_id, name, brand, type)
- `products` (product_id, store_id, name, brand, image)
- `observations` (run_id, store_id, product_id, price, original_price, stock, timestamp, discount_price, discount_promotion, discount_effective, discount_source, promotion_type, promotion_label, query_term)
- `runs` (run_id, started_at, finished_at, lat, lng, radius, vertical, status)

## Flujo del Crawler
- Se crea un Run (RUNNING)
- Itera sobre verticals, usa seeds hardcodeados como queries iniciales.
- Ejecuta `fetch_unified_search`
- Extrae productos y tiendas, realiza "keyword expansion" para añadir queries a la lista, evalúa rate limit y state (LOW_COVERAGE, SATURATED, etc.)
- Marca Run como COMPLETED.

## Histórico
- Calcula histórico analizando queries SQL con grouping manual en Python por (store_id, product_id).
- Calcula median_30d, median_7d, change_24h, historical_min, historical_max, historical_discount, deal_score, estado (NEW_LOW, REAL_DEAL, GOOD_DEAL, RAPPI_PROMO, NORMAL, INSUFFICIENT_HISTORY).

## Formatos de Salida
- `rappi-ofertas`: Logs directos por stderr (`print(..., file=sys.stderr)`) y no produce output estructurado de resultados directamente.
- `rappi-historico`: Formato tabla manual en stdout (si no hay `--json`), guarda archivo `history-analysis.json` obligatoriamente, e imprime resumen por stderr.

## Tests Existentes
- Hay una carpeta `tests` pero no sabemos qué contiene. Vamos a investigar en un momento, pero a simple vista parece que los tests no cubren todo lo que se pide.

## Comportamiento de Saturación
- Monitorea % de productos nuevos descubiertos. Si baja del 3%, marca `SATURATED`.

## Rate Limiting
- Captura HTTP 429 y 1015, retorna "RATE_LIMIT" y detiene la búsqueda limpiamente. Duerme 3s entre requests.

## Funcionalidades Solicitadas que ya existen parcialmente
- Búsqueda / Crawler discovery (keyword expansion)
- Descuentos directos y promocionales
- Ordenamiento y puntuación básica (deal score) en `rappi-historico`.
- Detección de Rate Limits.
