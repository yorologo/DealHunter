# Snapshot histórico del proyecto (v2 era)

> [!IMPORTANT]
> Este archivo conserva una auditoría histórica anterior a la arquitectura
> multiprovider. No describe el estado actual. Para el RC vigente consulte
> `README.md`, `docs/ARCHITECTURE.md` y el schema ejecutable en
> `src/dealhunter/db.py`.

## Resumen General
**Rappi Deal Hunter** es un rastreador (crawler) automatizado en Python diseñado para el entorno Termux. Evolucionó de una simple PoC de descubrimiento de tiendas a un motor analítico de precios históricos completo (v2).

## Estructura y Archivos Existentes
- `bin/rappi-ofertas`: Script ejecutable principal del Crawler (v1/v2). Descubre tiendas, recupera catálogo estructurado y alimenta la base de datos en pasadas orgánicas por "verticales".
- `bin/rappi-historico`: Script ejecutable analítico (v2). Computa medianas temporales (7d/30d), verifica mínimos históricos y clasifica la autenticidad de las ofertas (`NEW_LOW`, `REAL_DEAL`, `RAPPI_PROMO`).
- `scripts/auxiliary/`: Contiene scripts de investigación, pruebas exploratorias de red y migraciones de DB (Deal Hunter v1, archivos de investigación auxiliares).

## Endpoint Utilizado (Fuente de verdad)
- `POST https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search`
- **Flujo de datos**: CLI -> API Search -> Normalización JSON -> Motor de Descuentos (NxM) -> Inserción/SQLite -> Herramienta Histórica.

## Esquema SQLite (`rappi-deals.db`)
- `runs`: Metadatos de ejecución (tracking temporal).
- `stores`: Catálogo de tiendas únicas.
- `products`: Catálogo deduplicado por `(store_id, product_id)`.
- `observations`: Histórico *append-only* que mapea las capturas temporales asociadas a un `run_id` específico.

## Funcionalidades Implementadas
- **Búsqueda estructurada adaptativa**: Extrae ofertas sin necesidad de dependencias UI/Accessibility u OCR.
- **Deduplicación Intra-run**: Impide observaciones repetidas del mismo producto en la misma ejecución (`UNIQUE(run_id, store_id, product_id)`).
- **Protección Antifraude (Deal Engine)**: Desambigua descuentos mostrados por Rappi verificándolos matemáticamente (NxM y precio rebajado) y los comprueba contra su propia mediana empírica histórica.
- **Protección HTTP 429**: Termina el barrido ordenadamente al saturarse o chocar con límites de IP de Cloudflare.

## Deuda Técnica / Limitaciones
- Carece de despliegue multihilo debido a la fragilidad del Rate Limiter.
- Dependiente de la cobertura circular del endpoint de búsqueda (es heurístico, no garantiza el 100% de la tienda en una sentada).
