# DEALHUNTER_PHASE5C_UBER_SHADOW_ADAPTER

> [!IMPORTANT]
> Historical phase snapshot. It records the evidence and constraints observed in
> that phase; it is not current operational guidance. Current RC truth is
> v3.2.0 / schema v16: Rappi and Uber acquisition are production-capable, while
> canonical matching remains shadow-only, automatic writes are OFF, human
> ground truth is insufficient and the statistical gate is `NOT_MET`.


## PARSER
- **payload**: Se consume exitosamente el JSON estructurado de `getStoreV1`. Transport separado del normalizer.
- **sections**: Extraídas correctamente de `data.catalogSectionsMap` usando `VERTICAL_GRID` y `HORIZONTAL_GRID`.
- **products**: Extraídos sin pérdida. Los `catalogItems` contienen todo lo necesario.
- **unknown containers**: Se implementó una exclusión segura para elementos tipo `EATER_MESSAGE` u otros desconocidos para que no causen crashes.
- **Unicode**: Soporte completo a Unicode (acentos, emojis, etc.) preservado por la serialización JSON pura.
- **errors**: 0 errores en la ingestión de los fixtures validados.
- **performance**: Ingestión de un JSON de 800+ KB en menos de 0.1 segundos. Parseo y normalización extremadamente rápidos (O(N) sobre productos).

## IDENTITY
- **storeUuid**: Conservado puro de Uber (`raw_store_id`).
- **productUuid**: Conservado puro de Uber (`raw_product_id`).
- **provider provenance**: El Parser inyecta implícitamente `provider = "uber_eats"` en la memoria durante la normalización Shadow, pero *no existe* columna en v14 DB para guardarlo.
- **cross-store**: Aún sin evidencia en la muestra de que el `productUuid` de un local (ej. Dominos A) sea igual al de (Dominos B). Se mantendrá en contexto *por local* para evitar colisiones.
- **collisions**: Potencial alto de colisión si no se namespaces. (Rappi `product_id=123` vs Uber `product_id=123`).
- **recommended model**: Requerirá esquema V15 (añadir columna `provider`) para evitar colisiones de `PRIMARY KEY (store_id, product_id)`.

## PRICING
- **current**: Derivado de `price / 100.0`. Exacto y confiable.
- **reference**: Se deriva limpiamente del fallback `priceTagline.accessibilityText` cuando existe descuento (Regex safe).
- **accessibility fallback**: Funciona perfecto ("discounted from $120.00"). No depende de localización si el patrón numérico es predecible, pero actualmente se enfocó en el símbolo `$` y el texto base. 
- **discount**: Calculado idéntico a Rappi usando `current` y `reference`.
- **invalid samples**: Validado lógicamente (si `reference_price` < `current_price`, se revierte al current_price y se marca fallback_override).

## PROMOTIONS
- **product**: Identificado si el campo `promotionUUID` está presente.
- **NxM**: Aún no estructurado firmemente en esta muestra, se tratará a nivel título de producto (adaptación).
- **cart**: Aislado bajo `EATER_MESSAGE`, ignorado a nivel de producto.
- **Uber One**: Las secciones llamadas "Exclusivas de Uber One" indican membresía, no precio base universal. Semantic adaptation requerida.
- **promotion UUID**: Retenido en `promotion_label`.

## AVAILABILITY
- **isSoldOut**: Invertido limpiamente a `UNAVAILABLE` (0 stock) / `AVAILABLE` (1 stock).
- **unknown**: Para items sin esta bandera se asume `UNKNOWN`.
- **completeness**: Dictado por el payload capturado.

## TAXONOMY
- **grids**: Vertical y Horizontal grids parseados.
- **categories**: Derivadas de `payload.standardItemsPayload.title.text` en cada grid.
- **collections**: Mapeables a taxonomía interna.
- **unknown**: Ignorado sutilmente.

## SHADOW
- **stores**: 2 generadas (Dominos, Tortas Valdepeñas).
- **products**: 148 procesados sin pérdida.
- **observations**: 148 observaciones generadas exitosamente.
- **memberships**: Posible adaptación desde `category_source`.
- **duplicates**: No encontrados en la muestra (grids mutuos aislados).
- **errors**: 0.

## PARITY
- **direct**: Store, Product, Observation, Price, Discount, Taxonomy, Availability.
- **adapted**: Reference Price (de estructurado a fallback de accessibility).
- **provider-specific**: Uber One exclusivities.
- **unsupported**: NxM nativo (requiere más fixtures).

## CORE
- **Store / Product / Observation**: Compatibilidad total con diccionarios de normalización.
- **Query / Deal Score / Alerts**: Funcionarían idéntico gracias a los datos base limpios, siempre que estén en la DB.

## SCHEMA
- **v14 sufficient**: **NO**.
- **provenance**: No hay espacio para indicar `provider = 'uber_eats'`.
- **identity isolation**: Las claves primarias de V14 (`store_id`, `product_id`) colisionarán eventualmente sin namespace.
- **migration needed**: **V15 ES NECESARIO**.
- **reason**: Añadir la columna `provider` a `stores`, `products`, y `observations` (y sus PRIMARY KEYS/UNIQUE constraints). Sin ella, mezclar datos de Rappi y Uber corromperá el historial.

## QUALITY
- **starting tests**: 400
- **ending tests**: 405
- **failures**: 0
- **clean clone**: Posible, los test usan payload fixtures simulados.
- **Rappi regression**: 0% (namespace y tests aislados).

## SECURITY
- **secrets**: 0 (todo se hace offline).
- **payload**: Guardado fuera del git track en `~/.local/share/DealHunter/research/`.
- **result**: Seguro.

## DECISION
- **adapter validated**: YES.
- **normalization validated**: YES.
- **schema decision**: **B. SHADOW_ADAPTER_VALIDATED_MINIMAL_V15_REQUIRED**
- **ready for controlled integration**: Yes, pending V15 migration.
- **blockers**: Database Schema v15 (provider context).
