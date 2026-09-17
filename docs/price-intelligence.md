# Price Intelligence

El motor de **Price Intelligence** combate la manipulación de "precios originales" evaluando precios actuales contra el histórico empírico del producto en la misma tienda.

## Estados Documentados

```mermaid
flowchart TD
    CURRENT[Precio actual]
    HISTORY[Histórico]
    MEDIAN[Mediana 30d]
    MIN[Mínimo histórico]

    CURRENT --> PI[Price Intelligence]
    HISTORY --> PI
    MEDIAN --> PI
    MIN --> PI

    PI --> NEWLOW[NEW_LOW]
    PI --> REAL[REAL_DEAL]
    PI --> GOOD[GOOD_PRICE]
    PI --> NORMAL[NORMAL]
    PI --> INSUFFICIENT[INSUFFICIENT_HISTORY]
```

- `INSUFFICIENT_HISTORY`: Menos de 3 observaciones o < 1 día de historial.
- `NEW_LOW`: Precio actual es inferior al mínimo histórico anterior.
- `REAL_DEAL`: Precio actual es ≥ 15% inferior a la mediana móvil de los últimos 30 días.
- `GOOD_PRICE`: Precio actual es ≥ 5% (pero < 15%) inferior a la mediana de 30 días.
- `NORMAL`: No presenta ventaja histórica demostrable.

### Indicadores Flag

DealHunter reporta advertencias adosadas al estado principal.
- `SUSPICIOUS_REFERENCE_PRICE`: Se levanta si el "precio original" anunciado por el supermercado supera ampliamente el máximo histórico registrado para ese producto, sugiriendo inflación artificial.

## Descuentos

Los descuentos se normalizan usando fórmulas comprobables:
- **Descuento directo**: `(1 - price / original_price) * 100`
- **Promociones NxM**: `(1 - units_condition / promotion_value) * 100` (Ej. `2x1` = 50%, `3x2` = 33.33%)

El core nunca suma descuentos incompatibles y presenta el `effective_discount` priorizado.

## Price Integrity Contract

DealHunter almacena estrictamente lo que Rappi cobra. Si existe un precio final explícito que concuerda con la metadata (con un margen mínimo de redondeo), se utiliza como fuente de verdad. Si existe discrepancia severa (ej. glitch de divisas devolviendo USD en lugar de MXN), DealHunter reconstruye el precio base usando el descuento oficial (`discount` fraccional + `real_price`). Nunca se mezclan monedas o entidades incompatibles.

## Deal Score y Confidence

Para ordenar las oportunidades globales sin depender solo del porcentaje de descuento, DealHunter implementa **Deal Score V1**, identificado en código como `deal-score-v1`:
- **Economic Discount (0–60)**: usa el mejor descuento demostrable entre histórico y referencia promocional no sospechosa.
- **Market Bonus (0–30)**: recompensa ventaja contra equivalentes comparables; mercado ausente no infla otros componentes.
- **Timing/Event (0–10)**: `NEW_LOW` suma 10 y `REAL_DEAL` suma 5.
- **Confidence**: se calcula aparte con observaciones y días de histórico. No multiplica ni altera el número del score; sólo limita etiquetas de alta valoración cuando la evidencia es baja.

El algoritmo es determinista y está congelado por un corpus de regresión en `tests/corpus/deal_score_v1.json`. Cualquier cambio de pesos, thresholds o semántica requiere una nueva versión explícita del algoritmo y actualizar ese corpus; no se usa ML.
