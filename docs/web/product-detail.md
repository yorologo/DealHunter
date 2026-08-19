# Product Detail

La vista de detalle de producto (`/products/<store_id>/<product_id>`) es el hub central para analizar el comportamiento del precio de un ítem.

## Jerarquía UX
La información se presenta priorizando la acción y justificación:
1. **Decisión:** Precio actual, badges visuales (`REAL_DEAL`, `NEW_LOW`), y status atípicos.
2. **Explicación:** Módulo con la razón calculada por Price Intelligence.
3. **Exploración:** Tabs para (Resumen, Histórico, Comparar, Observaciones).

## Componentes Técnicos
- **Historical Chart (Chart.js):** Renderizado offline, interactivo con Tooltips (Fecha, Precio, Original/Promo), soporta cambio de rangos de visualización (`7D`, `30D`, `90D`, `Todo`). Usa client-side filtering para no golpear la base de datos repetidamente en cambios visuales.
- **Alerts & Watchlist:** Si el producto está trackeado, muestra el target configurado. Resumen de las notificaciones sin leídas para este ítem.
- **Empty States:** Manejo explícito de la falta de datos (`INSUFFICIENT_HISTORY` si el producto tiene menos de 2 muestras de precio separadas, como fue diseñado en v2.4).
- **Responsive:** Las métricas clave del "Resumen" pasan de una cuadrícula de 4x2 a un apilado vertical scrollable en pantallas pequeñas (`< 768px`). La gráfica reescala el canvas automáticamente.

## Limitaciones Fase B
- No se integra UI para añadir *directamente* alertas o watchlists complejas.
- La navegación horizontal de observables se hace vía tab, no infinite-scroll.
