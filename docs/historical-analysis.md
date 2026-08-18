# Análisis Histórico e Identificación de Fraudes de Precio

La v2 delega a la base SQLite un append-only diario. El script analítico `rappi-historico` lee esto para contrarrestar "inflación de descuentos".

## Lógica Temporal de Cálculo
Para cada tupla `(store_id, product_id)` se recuperan y se ordenan temporalmente las `observations`:
1. `median_30d` / `median_7d`: Precio mediano de los últimos 30 y 7 días.
2. `historical_min`: El límite de base registrado.
3. Se desecha `original_price` de la API para computar el "descuento verdadero" (`historical_discount = (1 - current_price / median_30d) * 100`).

## Estados Algorítmicos (`status`)
Dependiendo de esta contrastación y el límite mínimo de días (`--min-history-days`, por defecto 1), un producto cae en uno de estos cubos:

* **INSUFFICIENT_HISTORY:** No se le puede asignar estatus de promoción sin riesgo de caer en falso positivo por no existir suficiente vida histórica registrada.
* **NEW_LOW:** El precio en carrito de esta iteración está inferior al mínimo histórico.
* **REAL_DEAL:** El `historical_discount` supera el 50% de la mediana temporal (Oferta irrefutable comprobada empíricamente).
* **GOOD_DEAL:** Igual, pero el descuento efectivo es superior a 30%.
* **RAPPI_PROMO:** El API de Rappi reporta un `current_discount` >50% (generalmente por NxM o precios tachados inflados), pero que **NO** son verdaderos bajones del mínimo histórico en nuestra DB.
* **NORMAL:** Mercado flat.

## El `deal_score`
Una vez clasificados, reciben de `0` a `100` puntos mediante heurística sumativa que otorga altos bonos (hasta +60) a los `historical_discount` y la profundidad de sus datos (hasta +10 por tener muchas observaciones previas).
