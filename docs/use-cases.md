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

## Caso D — Comparación Cross-Store y Precio Unitario
**Ejemplo conceptual:**
* "Coca Cola 2 L" en Tienda A cuesta $50 ($25/L)
* "Coca Cola 2000 ml" en Tienda B cuesta $42 ($21/L)
* "Coca Cola 2 L" en Tienda C está en 2x1 (precio base $100 -> Efectivo $50).

DealHunter normaliza el nombre a `coca cola`, la cantidad a `2`, y la unidad a `L`. Usando el comando de comparación, unifica estos productos bajo el mismo grupo semántico utilizando un motor de matching conservador (EXACT / HIGH_CONFIDENCE), e indica que la Tienda B tiene el `BEST PRICE` con una diferencia porcentual para el resto.

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

### Caso 12: Watchlist
```bash
rappi-ofertas watch add "Café" --below 100
rappi-ofertas watch list
```

### Caso 13: Actualizar Histórico
```bash
rappi-ofertas update --dry-run
```

### Caso 14: Comparar tiendas
Descubre la tienda con el mejor precio para un producto equivalente:
```bash
bin/rappi-historico compare "Coca Cola"
bin/rappi-historico compare "leche" --exact-only
```

## Caso G — Encontrar promociones en Restaurantes
**Objetivo:** El usuario quiere ver ofertas de hamburguesas en restaurantes cercanos con al menos 20% de descuento.
**Flujo:**
```bash
rappi-ofertas restaurants --query "hamburguesa" --min-discount 20
```
1. El motor rastrea el catálogo de restaurantes y normaliza los precios.
2. Identifica combos, descuentos y promociones de `discounts_bundle`.
3. Filtra y muestra únicamente los platillos que cumplen el criterio.
