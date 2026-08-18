# Roadmap

## Implementado
* Extracción asíncrona de la API Unified Search.
* Estandarización matemática de bundles (NxM).
* Deduplicación de catálogo base (`store_id`, `product_id`).
* Soporte SQLite persistente (`runs` y `observations`).
* Búsqueda heurística por colas adaptativas.
* Identificación de "huecos" (tiendas con menos de 10 productos forzadas a expandirse).
* Analizador Histórico offline (`rappi-historico`).

## En consideración
* **Automatización local nativa (Scheduling):** Crear demonios transparentes para Linux/Termux.
* **Export CSV:** Convertir la salida del JSON de histórico a planillas compatibles con Excel/Pandas.
* **Alertas Inteligentes:** Integración con un webhook de Telegram para enviar un ping cuando se detecte un estado `NEW_LOW` que exceda un umbral mínimo de score.
* **Comparación Inter-tienda:** Mapeo de un mismo SKU entre diferentes supermercados para calcular arbitraje local de precios.
