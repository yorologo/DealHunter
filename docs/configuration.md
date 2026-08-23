# Configuration

DealHunter soporta configuración dinámica a nivel global y mediante perfiles específicos que priorizan overrides vía CLI.

Precedencia vigente:
`CLI > Profile > Global (config.toml) > Default`

La UI de administración web presenta y clarifica el **valor efectivo** que el crawler asume al momento, junto con el **origen**.

## Variables de Entorno Seguras
Para proteger secretos, no los definas en `config.toml`. 
El token debe exportarse en terminal antes de ejecutar (Ej: `RAPPI_BEARER_TOKEN="tu_token_aqui" bin/rappi-ofertas ...`).

## Ejemplos de Ajustes Seguros (`SAFE_EDITABLE`)
- `lat`, `lng`: Ubicación de entrega usada por el crawler. Son obligatorias para capturas reales y deben corresponder a la dirección activa de Rappi.
- `min_discount`: Descuento mínimo para mostrar en Oportunidades y Vistas (0 a 100). No impide la ingesta del Crawler.
- `max_requests`: Cuota (budget) máxima de consultas HTTP por run.
- `radius`: Cobertura del rastreador.
- `compact`: Estilo de visualización terminal.

## Ubicación Canónica

Configura una sola vez los valores personales en el archivo global local mediante la CLI; no los añadas al repositorio:

```bash
bin/rappi-ofertas config set lat TU_LATITUD
bin/rappi-ofertas config set lng TU_LONGITUD
bin/rappi-ofertas discover --vertical general
```

El cron debe omitir `--lat/--lng` para consumir exactamente este `config.toml`. Un override CLI sigue teniendo prioridad para una ejecución deliberada. Cada run guarda su ubicación en `runs.lat/runs.lng`. Si el punto nuevo queda a 500 m o más del último run, DealHunter advierte el cambio y preserva el histórico; nunca borra filas automáticamente.

- La sesión determina el modo del crawler de forma automática.

## Schema 8 Additions
- `stores.status`: (TEXT) ACTIVE, STALE, UNKNOWN.
- `stores.last_seen_at`: (DATETIME).
- `runs.crawler_mode`: (TEXT) ZONE_INVENTORY o SEARCH_DISCOVERY.
- `runs.coverage_complete`: (INTEGER) 0 o 1.

*Migración idempotente desde v7. Preserva observaciones e histórico.*
