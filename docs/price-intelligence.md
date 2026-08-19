# Price Intelligence Engine (v2.4)

El motor de **Price Intelligence** evalúa históricamente el precio de los productos para detectar oportunidades reales y clasificar los descuentos de forma conservadora. Se basa únicamente en la historia comprobable dentro de SQLite.

## Métricas Históricas

Para cada producto con historial (≥3 observaciones y >24 hrs de separación), se calcula:
- **`current_price`**: Precio de la observación más reciente.
- **`historical_min`** / **`historical_max`**: Extremos históricos absolutos.
- **`median_30d`**: Mediana de las observaciones de los últimos 30 días.
- **`historical_average`**: Promedio histórico total.
- **`price_change`** y **`price_change_percent`**: Diferencia vs la observación inmediatamente anterior.
- **`discount_vs_median_30d`**: Descuento porcentual contra la mediana de los últimos 30 días.
- **`distance_from_historical_min`**: Distancia porcentual hacia el mínimo histórico.

## Clasificación de Ofertas (Status)

Cada producto recibe un único estado `status` según reglas estrictas:

- **`NEW_LOW`**: El `current_price` es menor al mínimo histórico anterior (requiere que la base ya tuviera precios previos superiores).
- **`REAL_DEAL`**: El precio es claramente inferior a la tendencia: `discount_vs_median_30d >= 15.0%`.
- **`GOOD_PRICE`**: El precio es moderadamente inferior a la tendencia: `discount_vs_median_30d >= 5.0%`.
- **`NORMAL`**: Sin ventaja histórica demostrable (fluctuaciones menores al 5% o precios más altos).
- **`INSUFFICIENT_HISTORY`**: Menos de 3 observaciones o historia registrada en menos de 1 día (24 hrs). Evita generar falsos positivos por falta de datos.

## Suspicious Reference Price

El motor alerta (marca `is_suspicious_reference = True`) si un proveedor reporta un `original_price` (precio tachado/anunciado) exagerado.
- **Regla**: `original_price > historical_max * 1.2`
- Si la tienda afirma que el producto costaba \$150, pero en todo el historial registrado por DealHunter nunca superó los \$110, se levanta este flag. Esto no acusa fraude, sino que alerta una "inconsistencia con el histórico".

## Cross-Store Historical Comparison

El CLI `bin/rappi-historico compare` y `deals` integran estas métricas. En la comparación multi-tienda:
- Se agrupan productos equivalentes usando el motor de matching.
- Se selecciona el de menor precio (`best_current_price`).
- Se expone visualmente el `MEDIAN_30D`, `HIST_MIN` y el `VS_MEDIAN`.
- Se expone el `STATUS` histórico.

## Limitaciones
- **Temporalidad**: La detección de anomalías depende directamente del crawling continuo. Un producto monitoreado esporádicamente puede tener `INSUFFICIENT_HISTORY`.
- **Inflación**: La mediana a 30 días es más robusta que el promedio, pero no contempla inflación a muy largo plazo.
