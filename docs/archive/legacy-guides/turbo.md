# Rappi Turbo Integration

DealHunter incluye soporte integral para **Rappi Turbo** como una vertical de primer nivel a partir de v2.2.

## Identificación y Normalización
A diferencia de tiendas como supermercados, los identificadores de Turbo en Rappi se etiquetan típicamente como:
- `parent_store_type`: `chiper_home`, `chiper_extended`, o `chiper`.
- El nombre de la tienda suele contener "Turbo".

Afortunadamente, los productos devueltos por el endpoint unificado conservan el **mismo modelo de datos** (categoría, precio, `real_price`, `discounts_bundle` para NxM). DealHunter inyecta estos resultados transparentemente a su `Discount Engine`, normalizando y validando los datos de la misma manera.

## Uso Básico
Para rastrear exclusivamente tiendas Turbo:

```bash
rappi-ofertas discover --vertical turbo
```

O para actualizar precios conocidos de Turbo:

```bash
rappi-ofertas update --vertical turbo
```

## Compatibilidad
La vertical Turbo es completamente compatible con los filtros existentes:
- `--min-discount`, `--max-discount`
- `--only-nxm`, `--promo`
- `--query`, `--min-price`, `--max-price`
- `--dry-run`, `--max-requests`

## Histórico Offline
Las observaciones capturadas de tiendas Turbo persisten y se entrelazan de manera transparente dentro del ecosistema de histórico de precios (`observations` table). DealHunter es capaz de marcar de forma automática `NEW_LOW` o `REAL_DEAL` basándose en el historial.
