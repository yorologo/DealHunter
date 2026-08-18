# Glosario de Términos

* **CPG (Consumer Packaged Goods):** Bienes de consumo empaquetados. Categoría interna comúnmente usada por supermercados y farmacias.
* **SKU (Stock Keeping Unit):** El código único de barras o identificador físico de un producto.
* **store_id:** Identificador interno numérico de una tienda específica. Dos sucursales de Chedraui tendrán distinto `store_id`.
* **product_id:** Identificador interno numérico de un producto. Sólo es único en combinación con el `store_id`.
* **vertical:** Una categoría semántica de búsqueda (ej. `farmacia`, `mascotas`). El crawler usa diccionarios distintos para cada vertical.
* **run:** Una ejecución individual del crawler (un barrido de zona). Produce un `run_id` único.
* **observation:** El estado de un producto (precio y stock) registrado en el instante específico de un `run`.
* **price:** Precio final al que se vende el producto en este instante.
* **original_price:** El precio tachado o "de lista" que sugiere la plataforma. Puede estar artificialmente inflado.
* **promotion:** Promociones etiquetadas aplicables al producto (ej. "2x1", "Lleva 3, Paga 2").
* **bundle:** Agrupación de items o promociones `NxM`.
* **NxM:** Promociones donde llevas N productos pagando M unidades (Ej. 3x2, llevas 3 pagas 2).
* **discount_price:** Descuento porcentual calculado usando `price` vs `original_price`.
* **discount_promotion:** Descuento porcentual extraído algebraicamente de un paquete `NxM`.
* **discount_effective:** El mayor valor legítimo entre `discount_price` y `discount_promotion`. Es el descuento máximo garantizado en la compra.
* **historical_discount:** Descuento real calculado contrastando el `price` actual contra la mediana histórica almacenada en la base de datos local. Evade la manipulación del `original_price`.
* **median_7d / median_30d:** El precio mediano al que se ha vendido el producto en los últimos 7 o 30 días. Suaviza picos y valles de ofertas de corta duración.
* **novelty rate:** El porcentaje de productos *completamente nuevos* que una búsqueda (keyword) aportó a la base de datos, contra el total de productos que devolvió. Mide la rentabilidad de seguir buscando.
* **saturation:** Estado en el que el `novelty_rate` cae sostenidamente por debajo del 3%. Significa que las consultas sólo están trayendo productos duplicados (ya conocidos) y el crawler debe detenerse.
* **rate limiting:** Restricción de velocidad impuesta por servidores (ej. WAF Cloudflare) para bloquear tráfico automatizado (códigos de error 429 o 1015). DealHunter lo respeta orgánicamente.
