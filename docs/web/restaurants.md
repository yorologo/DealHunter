# DealHunter Restaurants Experience

La fase B3 implementó una experiencia de restaurante dedicada, diferenciándola completamente del modelo de supermercado.

## Precio Base y Toppings / Modificadores
DealHunter no puede scrapear ni indexar todas las combinaciones posibles de toppings, extras y modificadores de platillos (ej. "combo arma tu gusto").
Por lo tanto, hemos establecido las siguientes reglas:
- **Precio Base**: USAMOS ESTRICTAMENTE metadata estructurada del origen (has_toppings). NUNCA inferimos ni inventamos atributos por NLP/palabras clave.
- En la interfaz, mostramos explícitamente "Precio base" y advertimos que el precio "Puede cambiar al seleccionar opciones".
- **Histórico**: Solo se realiza y muestra análisis de inteligencia de precios para el "Precio base" capturado.

## Availability y Stock NULL
A diferencia de un supermercado, los platillos de restaurante rara vez tienen inventario numérico (stock).
- Si `stock = NULL`, no mostramos métricas numéricas engañosas ni la etiqueta "Stock detectado".
- Nos apoyamos enteramente en el flag de disponibilidad (availability = `AVAILABLE` / `UNAVAILABLE`).
- Los componentes visuales (ej. `dish_card`) muestran claramente el platillo atenuado (opacidad reducida) y con un badge de "Agotado / No disponible" si `availability == 'UNAVAILABLE'`.

## Promociones Soportadas
- **Direct discount (Descuento directo)**: Promociones a nivel de platillo se muestran en el card mediante badges dedicados y tachando el precio original.
- **Limitación Global**: DealHunter NO imputa descuentos globales (ej. envío gratis, descuentos de carrito o mínimos de orden) al precio base del platillo.

## Categorías de Menú
- Se corrigió el modelo semántico: `category_name` ahora fluye desde la API, se guarda en SQLite (`products.category`) y sirve como eje taxonómico principal.
- Los platillos se agrupan en su vista de detalle de restaurante usando su categoría original del proveedor. Los que carecen de categoría se agrupan bajo "Otros" (Uncategorized).
