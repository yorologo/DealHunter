# Product Normalization

DealHunter v2.3 introduces a robust product normalization layer designed to extract and standardize brands, units, and quantities from raw product titles, allowing for fair cross-store comparisons.

## Reglas de Parsing

El motor analiza el `name` del producto y el campo estructurado `brand` del endpoint de Unified Search para extraer información estructurada:

1. **Brand**: Se respeta el metadata estructurado si está presente, de lo contrario se deduce del string (futuro). Todo se lleva a lowercase.
2. **Quantity & Unit**: Usando Regex para identificar patrones comunes como `2 L`, `500 ml`, `6 pack 355 ml`, `12 piezas`.
3. **Normalized Name**: Se remueve la cantidad/unidad explícita del nombre del producto y caracteres especiales extraños.

## Unidades Soportadas

Actualmente DealHunter soporta la extracción y normalización de:
* Peso: `g`, `mg` → `kg`
* Volumen: `ml` → `L`
* Unidades: `pz`, `pza`, `piezas` → `pieza`
* Médico: `tableta`, `tabletas`, `cápsulas`, `capsula`
* Agrupación: `pack` (ej. `6 pack 355 ml` se expande a `2.13 L` si se especifica submúltiplo).

### Ejemplos Normalizados

| Raw Name | Brand | Normalized Name | Qty | Unit | Norm Qty | Norm Unit |
|----------|-------|-----------------|-----|------|----------|-----------|
| Coca Cola 2L | Coca-Cola | coca cola | 2 | L | 2 | L |
| Coca-Cola 2000 ml | Coca-Cola | coca-cola | 2000 | ml | 2 | L |
| Arroz 900 g | - | arroz | 900 | g | 0.9 | kg |
| Croquetas 3 kg | - | croquetas | 3 | kg | 3 | kg |
| Refresco 6 pack 355 ml | - | refresco | 2130 | ml | 2.13 | L |
| Huevos 12 piezas | - | huevos | 12 | pieza | 12 | pieza |

## Unit Price (Precio Unitario)

La CLI ahora es capaz de calcular el precio unitario (`UNIT_PRICE`) de manera determinista al usar `rappi-historico`.

Ejemplo:
* `$180 / 2 L` → `$90.0 / L`
* `$60 / 12 piezas` → `$5.0 / pieza`

Puedes usar el parámetro de CLI `--sort unit-price` para priorizar los productos con el precio unitario más bajo. Los productos con cantidades ambiguas (donde no se puede calcular) se ubican al final del sorting de forma segura.

## Product Fingerprint

Se crea un fingerprint conservador concatenando `brand|normalized_name|normalized_quantity|normalized_unit`.

Ejemplo conceptual:
* `coca-cola|original|2|l`

> [!NOTE]
> DealHunter actualmente utiliza coincidencias exactas para los fingerprints. Dos productos compartirán fingerprint solamente si su cadena generada coincide. Todavía no se usa Fuzzy Matching.

## Limitaciones

* **Fuzzy Matching**: Aún no está implementado. `coca cola` y `coca-cola` podrían generar diferentes fingerprints.
* **Toppings (Restaurantes)**: No se normalizan ni soportan variantes dentro de un mismo producto; se asume siempre el precio/cantidad base del platillo.
* **Ambigüedad**: Si un producto no especifica claramente su unidad (ej: `Leche Entera`), la normalización fallará de forma segura (`quantity = NULL`), deshabilitando el cálculo de `UNIT_PRICE`.
