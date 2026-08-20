# Configuration

DealHunter soporta configuración dinámica a nivel global y mediante perfiles específicos que priorizan overrides vía CLI.

Precedencia vigente:
`CLI > Profile > Global (config.toml) > Default`

La UI de administración web presenta y clarifica el **valor efectivo** que el crawler asume al momento, junto con el **origen**.

## Variables de Entorno Seguras
Para proteger secretos, no los definas en `config.toml`. 
El token debe exportarse en terminal antes de ejecutar (Ej: `RAPPI_BEARER_TOKEN="tu_token_aqui" bin/rappi-ofertas ...`).

## Ejemplos de Ajustes Seguros (`SAFE_EDITABLE`)
- `min_discount`: Descuento mínimo aceptado (0 a 100)
- `max_requests`: Cuota (budget) máxima de consultas HTTP por run.
- `radius`: Cobertura del rastreador.
- `compact`: Estilo de visualización terminal.
