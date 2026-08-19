# Product Normalization

DealHunter v2.3 normaliza marcas, cantidades, unidades y composición de packs antes de comparar productos entre tiendas. La representación conserva tanto la cantidad total como el número de unidades del pack: dos presentaciones con el mismo volumen por unidad no son necesariamente el mismo producto.

## Reglas de parsing

El motor analiza `name` y el campo estructurado `brand` del proveedor para obtener:

1. **Brand**: **NUNCA se inventa ni se deduce a partir del nombre del producto**. Proviene estrictamente de metadatos estructurados proporcionados por la API (el campo `trademark`). Si la API devuelve una marca válida, se normaliza. Si se actualiza el producto (UPSERT), se enriquece sin borrar valores previos.
2. **Quantity & Unit**: extrae la cantidad total y la unidad declarada.
3. **Normalized Quantity & Unit**: convierte `g` y `mg` a `kg`, y `ml` a `L`.
4. **Pack Count**: registra cuántas unidades individuales contiene una presentación explícita. Una cantidad sin multiplicador tiene `pack_count = 1`; si no hay información suficiente, queda `NULL`.
5. **Normalized Name**: elimina la expresión completa de cantidad/pack y canonicaliza el resto del título.

El schema SQLite v4 añade `products.pack_count INTEGER`. La migración es idempotente y conserva todos los productos y observaciones existentes. Los registros v3 quedan con `pack_count = NULL` hasta volver a normalizarlos; `scripts/backfill_normalization.py <db>` migra con backup previo y procesa únicamente filas que aún necesitan esos datos.

## Formatos soportados

Las expresiones de volumen incluyen `1 L`, `1 l`, `1 lt`, `2 lt` y sus equivalentes en `ml`. Los packs reconocidos incluyen:

- `2 x 1 L`
- `2x1 L`
- `2 x botella 1 L`
- `2 x 355 ml`
- `6 x 355 ml`
- `6 pack 355 ml`
- `Pack 2 botellas 1L`
- `Pack 6 latas de 355 ml`

Un multiplicador explícito sin tamaño, como `2 x Leche Deslactosada`, conserva `pack_count = 2`, pero mantiene cantidad y unidad desconocidas. No se inventa un volumen.

Las unidades normalizadas son:

- Peso: `g`, `mg` → `kg`; `kg` se conserva.
- Volumen: `ml` → `L`; `l`, `lt`, `litro` y `litros` → `L`.
- Unidades: `pz`, `pza`, `pzas`, `pieza`, `piezas` → `pieza`.
- Médico: `tableta(s)` y `cápsula(s)`.
- Pack sin subcantidad: unidad `pack`.

## Ejemplos

| Raw Name | Normalized Name | Total Qty | Norm Unit | Pack Count |
|---|---|---:|---|---:|
| Coca Cola 2L | coca cola | 2 | L | 1 |
| Coca-Cola 2000 ml | coca cola | 2 | L | 1 |
| Arroz 900 g | arroz | 0.9 | kg | 1 |
| Refresco 6 x 355 ml | refresco | 2.13 | L | 6 |
| Refresco Pack 6 latas de 355 ml | refresco | 2.13 | L | 6 |
| Leche 2 x botella 1 L | leche | 2 | L | 2 |
| Leche 1 lt | leche | 1 | L | 1 |

La cantidad normalizada de un multipack es total. Por ejemplo, `6 x 355 ml` produce `2.13 L` y `pack_count = 6`. Esto permite calcular el precio por litro sin perder la composición comercial.

## Precio unitario

`UNIT_PRICE` se calcula con la cantidad total normalizada:

- `$180 / 2 L` → `$90/L`
- `$60 / 12 piezas` → `$5/pieza`

Una cantidad ausente o no positiva produce `UNIT_PRICE = NULL`; esos productos quedan al final al ordenar por precio unitario.

## Fingerprint

El fingerprint contiene `brand|normalized_name|normalized_quantity|normalized_unit` y, para multipacks, añade `pack-N`.

Ejemplos:

- `coca-cola|original|2|l`
- `marca|refresco|2.13|l|pack-6`

El número de pack evita que un multipack actualizado comparta fingerprint con una unidad de igual volumen total. Además, el matcher ejecuta sus reglas duras antes de aceptar un fingerprint, para proteger registros antiguos.

## Comportamiento conservador

- Una unidad de `1 L` no coincide con `2 x 1 L`.
- `355 ml` no coincide con `6 x 355 ml`.
- Dos expresiones equivalentes, como `6 x 355 ml` y `Pack 6 latas 355 ml`, sí pueden coincidir.
- Cantidad o unidad desconocidas deshabilitan `HIGH_CONFIDENCE_MATCH` y `FUZZY_MATCH`. Sólo un fingerprint idéntico puede producir `EXACT_MATCH` en ese estado.
- No se infiere una marca ausente ni una cantidad implícita.

Los productos de restaurantes y toppings siguen requiriendo adaptadores específicos cuando su estructura no representa un SKU minorista normal.
