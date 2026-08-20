# Restaurants Web Experience

La vista de restaurantes refleja las categorías y menú de forma estructurada.

## Modificadores y Toppings
DealHunter emplea la bandera estricta `has_toppings` obtenida de la metadata estructurada del proveedor.
**No se utiliza NLP, análisis de texto, ni heurísticas (como "combo", "personaliza", "elige") para deducirlo.**

Cuando `has_toppings = true`, la UI advierte explícitamente: *"Precio base. Puede cambiar al seleccionar opciones."*

## Limitaciones Históricas
El tracker de precios y el histórico rastrean exclusivamente el **precio base**. DealHunter no consolida:
- Precios finales condicionados a múltiples toppings o exclusiones de menú.
- Delivery fee (costo de envío).
- Ratings o ETAs.
