# Alerts Engine

El motor local evalúa notificaciones sin utilizar infraestructura cloud. Se ejecuta en `src/dealhunter/alerts.py`.

## Tipos Soportados
- `TARGET_PRICE`: El precio baja a, o por debajo del, umbral del usuario establecido en la *Watchlist*.
- `NEW_LOW`: Mínimo histórico roto.
- `REAL_DEAL`: Ventaja estadística fuerte contra mediana móvil de 30 días.
- `PRICE_DROP`: Cualquier baja de precio consecutiva entre runs.
- `BACK_IN_STOCK`: El producto regresa al inventario tras registrar una observación de ausencia (stock depletion).

El motor persiste los eventos en la base local y mantiene deduplicación temporal, garantizando que el usuario no reciba la misma alerta por una promoción estática prolongada.

> NOTA: La gestión web (UI) completa y notificaciones push de Android están planificadas para v2.10.
