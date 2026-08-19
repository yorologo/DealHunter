# Product Matching

DealHunter v2.3 introduce un sistema de matching conservador para poder comparar el mismo producto a través de múltiples tiendas (ej. Supermercados, Farmacias, Rappi Turbo).

## Canonicalización

Antes de evaluar coincidencias, las cadenas de texto (marcas, nombres de producto) pasan por un proceso de canonicalización que:
1. Elimina acentos (`Coca Cola Clásica` → `Coca Cola Clasica`).
2. Convierte todo a minúsculas (`Coca-Cola` → `coca-cola`).
3. Reemplaza puntuación y caracteres especiales con espacios (`Coca-Cola` → `coca cola`).
4. Colapsa múltiples espacios.

## Tipos de Matching

Actualmente DealHunter implementa tres niveles de coincidencia deterministas:

### 1. EXACT_MATCH (Confidence: 1.0)
Los productos comparten exactamente el mismo `fingerprint` canónico generado a partir de:
* `brand`
* `canonical_name`
* `normalized_quantity`
* `normalized_unit`

### 2. HIGH_CONFIDENCE_MATCH (Confidence: 0.7 - 0.8)
Se permite cuando hay una leve variación en el nombre comercial reportado por diferentes tiendas, siempre y cuando coincidan estrictamente en:
* Marca (`brand`)
* Cantidad (`normalized_quantity`)
* Unidad (`normalized_unit`)
* Variantes principales (ej. `zero`, `light`, `entera`, `shampoo`) no entran en conflicto.

**Ejemplo Válido:**
* `Coca Cola Original 2 L`
* `Coca Cola Refresco Original 2000 ml`

### 3. FUZZY_MATCH (Confidence: 0.6)
Actúa estrictamente como un **fallback** cuando `EXACT` e `HIGH_CONFIDENCE` fallan. No pretende ser una IA generativa ni usar embeddings costosos; implementa la biblioteca estándar de Python (`difflib.SequenceMatcher`).
* Requiere que coincidan estrictamente **Marca, Cantidad y Unidad**.
* Requiere que **NO** existan conflictos de variantes semánticas ("Zero", "Original", "Entera", "Deslactosada").
* Útil para solventar typos simples o diferencias ortográficas (ej. `cacahuate` vs `cacahuete`, `coca colla` vs `coca cola`).

### 4. NO_MATCH (Confidence: 0.0)
El matching es conservador y se rechaza activamente si:
* Difieren en cantidad (ej. `600 ml` vs `2 L`).
* Las palabras clave semánticas entran en conflicto (ej. `Zero` vs `Original`, `Entera` vs `Deslactosada`, `Shampoo` vs `Acondicionador`).
* La marca registrada no coincide.

## Comparación entre Tiendas (Multi-store Comparison)

La CLI soporta la comparación del mejor precio para un producto a través de todas las tiendas sondeadas.

```bash
bin/rappi-historico compare "coca cola"
```

El motor agrupa automáticamente los `EXACT_MATCH` y `HIGH_CONFIDENCE_MATCH` bajo el mismo paraguas, indicando la mejor tienda, el mejor precio y la diferencia porcentual con respecto al resto.

**Salida Típica:**
```text
GRUPO                 TIENDA          PRECIO     DIFF     UNIT_PRICE  MATCH             PRODUCTO
Coca Cola Original    Soriana         $42.00     BEST     $21.00/L    EXACT             Coca Cola Original 2 L
Coca Cola Original    Chedraui        $45.00     +7.1%    $22.50/L    HIGH_CONFIDENCE   Coca-Cola Refresco Orig 2 L
```

### Opciones de CLI

* `--exact-only`: Limita la agrupación estrictamente a `EXACT_MATCH`, excluyendo variaciones de nombre y fuzzy.
* `--no-fuzzy`: Deshabilita el algoritmo de fallback fuzzy (mantiene `HIGH_CONFIDENCE`).
* `--format`: Soporta salidas en `json`, `csv`, o `table`.

## Limitaciones
1. **Fuzzy Matching Restringido**: El threshold es alto (>=0.85) para evitar falsos positivos costosos. No se usan LLMs ni Embeddings de NLP para asegurar que el motor opere de forma ligera y 100% offline.
2. **Presentaciones Agrupadas**: Un paquete de `6 x 355 ml` no se emparejará con un producto individual de `355 ml`. El cálculo unitario existe, pero el matching los aísla correctamente por diseño.
