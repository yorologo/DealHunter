# Casos de Uso

## Caso A — Encontrar promociones >= 50%
**Objetivo:** El usuario quiere comprar únicamente ofertas realmente agresivas y obviar descuentos del 5% o 10%.
**Flujo:**
1. Ejecutar el crawler en una ubicación.
2. El sistema recupera los productos.
3. El motor matemático (`discount_effective`) limpia las promociones engañosas.
4. El script filtra las que caen `>= 50%` y las muestra en la tabla final del escaneo.

## Caso B — Encontrar promociones NxM (Ej. 2x1)
Los supermercados suelen agrupar sus mejores promociones bajo la etiqueta "Lleva 2 y Paga 1". DealHunter parsea esto internamente como:
* `units_condition` = 1 (Pagas 1)
* `promotion_value` = 2 (Recibes 2)
* `discount_effective` = `(1 - 1/2) * 100` = **50%**
El sistema las iguala a un descuento de la mitad del precio, permitiéndote compararlas directamente con productos que tengan descuento tradicional.

## Caso C — Evitar confundir 3x2 con un "Súper Descuento"
Muchos usuarios perciben un 3x2 como un remate. DealHunter lo transparenta numéricamente:
* `3x2` significa que pagas 2 y recibes 3.
* Descuento = `(1 - 2/3) * 100` = **33.33%**.
La oferta se cataloga como inferior a un `2x1` y a un `-50%` directo, protegiéndote de comprar por volumen innecesario.

## Caso D — Comparar cadenas
**Ejemplo conceptual:**
* Producto X en Tienda A cuesta $50
* Producto X en Tienda B cuesta $42
* Producto X en Tienda C está en 2x1 (precio base $100).
DealHunter unifica la métrica en la tabla SQLite, permitiéndote consultar a nivel de base de datos (`product_id`) la observación más eficiente, que en este caso sería C ($50 efectivo por unidad).

## Caso E — Detectar oferta histórica (REAL_DEAL)
**Situación:**
* Precio habitual sostenido por 30 días: $100
* Precio actual repentino: $48
* `historical_discount` calculado = **52%**.
* Clasificación: `REAL_DEAL`.

## Caso F — Detectar promoción posiblemente engañosa
**Situación:**
* La plataforma muestra una insignia de **"60% OFF"**.
* Precio original (sugerido por el API): $150
* Precio actual: $60
* Sin embargo, la **mediana histórica** de ese producto los últimos 30 días ha sido de **$65**.
* Caída histórica real = **7.7%**.
* Clasificación: `RAPPI_PROMO`. El sistema ignora la insignia y te advierte que el precio habitual suele ser casi idéntico al actual. (Diferencia crítica entre `promo_status` provisto por el API vs `history_status` derivado empíricamente).
