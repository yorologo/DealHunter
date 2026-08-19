# Product Matching

DealHunter v2.3 compara productos entre tiendas con una política conservadora: una coincidencia aproximada sólo se evalúa después de aprobar marca, tamaño, pack y variantes semánticas. Ante información insuficiente, el producto queda separado.

## Canonicalización

Marcas y nombres:

1. pierden acentos;
2. se convierten a minúsculas;
3. sustituyen puntuación por espacios;
4. colapsan espacios repetidos.

Por ejemplo, `Coca-Cola Clásica` se convierte en `coca cola clasica`.

## Reglas duras

Antes de `EXACT`, `HIGH_CONFIDENCE` o `FUZZY`, el matcher rechaza:

- cantidad total o unidad distintas;
- tamaño conocido en un lado y desconocido en el otro;
- `pack_count` distinto o ausente para un tamaño conocido;
- marcas explícitas distintas;
- variantes semánticas incompatibles o presentes sólo en un lado.

La validación de packs ocurre antes del fingerprint. Así, un fingerprint v3 obsoleto no puede unir un pack de 2 con una unidad individual.

Las categorías de variante son pequeñas y deliberadamente testeables:

- fórmula: `original/clásica/regular`, `zero`, `light`, `diet`;
- azúcar: `sin azúcar`;
- leche: `entera`, `deslactosada/sin lactosa`, `descremada`, `semidescremada`;
- sabor: `fresa`, `chocolate`, `vainilla`, `capuccino` y equivalentes ortográficos;
- cuidado capilar: `shampoo`, `acondicionador`;
- etapa: `adulto`, `cachorro`.

Las equivalencias declaradas dentro de una categoría son compatibles. Cualquier perfil diferente —incluido explícito frente a ausente— bloquea HIGH/FUZZY. Por ejemplo, `Leche Deslactosada Semidescremada` no coincide con `Leche UHT Semidescremada Capuccino`.

## Tipos de matching

### EXACT_MATCH — 1.00

Requiere fingerprints idénticos y haber aprobado las reglas duras. El fingerprint incluye marca, nombre canónico, cantidad, unidad y `pack_count` cuando es mayor que uno.

Si ambos tamaños son desconocidos, sólo esta equivalencia exacta puede coincidir. Nombres distintos con tamaño desconocido nunca pasan a matching aproximado.

### HIGH_CONFIDENCE_MATCH — 0.70–0.80

Requiere como mínimo:

- marca explícita, no vacía e idéntica;
- cantidad total y unidad conocidas e idénticas;
- `pack_count` conocido e idéntico;
- ausencia de conflictos de variante;
- contenido semántico compartido suficiente.

Para calcular contenido compartido se excluyen términos genéricos como `leche`, `bebida`, `refresco`, `producto`, `pack`, `paquete`, `botella` y `lata`. Esas palabras no pueden generar confianza alta por sí solas. Una inclusión de palabras o un solapamiento del 60% sólo cuentan cuando existe al menos un término compartido significativo con cinco o más caracteres semánticos en total.

Ejemplo válido:

- `Coca Cola Original 2 L`
- `Coca Cola Refresco Original 2000 ml`

### FUZZY_MATCH — 0.60

Es un fallback para typos después de todas las reglas anteriores. Usa `difflib.SequenceMatcher` sin dependencias y conserva el threshold `0.85`.

La comparación fuzzy opera únicamente sobre palabras semánticas no genéricas. Cada nombre debe aportar al menos nueve caracteres alfanuméricos; esto impide usar similitud de edición en nombres demasiado cortos. Por eso `Pan Bollo` y `Bolillo Pan` se rechazan, mientras `cacahuete` y `cacahuate`, con la misma marca, tamaño y pack, pueden coincidir.

### NO_MATCH — 0.00

Representa tanto una incompatibilidad demostrada como una candidatura insuficientemente segura. DealHunter no expone un match aproximado para cantidades desconocidas, marcas ausentes, packs indeterminados, nombres cortos o variantes dudosas.

## Packs

- `2 x 1 L` vs `1 L` → `NO_MATCH`
- `6 x 355 ml` vs `355 ml` → `NO_MATCH`
- `2 x 1 L` vs `Pack 2 botellas 1L` → match permitido
- `6 x 355 ml` vs `Pack 6 latas 355 ml` → match permitido

El volumen total por sí solo no basta: `pack_count` forma parte de la identidad de presentación.

## Comparación entre tiendas

```bash
bin/rappi-historico compare "coca cola"
```

`--exact-only` conserva sólo `EXACT_MATCH`; `--no-fuzzy` admite EXACT/HIGH pero deshabilita FUZZY. Los formatos `table`, `json` y `csv` mantienen los datos operativos separados de stdout estructurado.

El agrupamiento sólo utiliza los tipos habilitados. Un `NO_MATCH` permanece en un grupo distinto, aunque el resultado sea conservador o ambiguo.
