# DealHunter v2.5 Alerts Engine

El motor de alertas (AlertEngine) monitorea constantemente los productos escaneados y los evalúa contra un set de reglas offline, persistiendo únicamente aquellas condiciones que representen valor accionable.

## Tipos de Alerta

- **`TARGET_PRICE`**: El precio de un producto cumple con el umbral esperado configurado en la watchlist. 
- **`NEW_LOW`**: El producto ha roto el mínimo histórico establecido (y cuenta con historial suficiente).
- **`REAL_DEAL`**: El producto presenta una disminución agresiva demostrable, generalmente superior al 15% vs la mediana móvil de los últimos 30 días.
- **`PRICE_DROP`**: Una simple métrica de cambio iterativo; el precio de un producto bajó abruptamente (por defecto ≥10%) respecto a su última observación, sin requerir romper records.
- **`BACK_IN_STOCK`**: Disponibilidad transicionando de `UNAVAILABLE` a `AVAILABLE`. 

## Deduplicación
Para evitar ruido excesivo, el motor aplica reglas de deduplicación persistentes (vía la tabla local `alerts`):
- Un producto no generará notificaciones redundantes del mismo tipo, si la última notificación de ese tipo no ha visto un descenso adicional en el precio.
- Ejemplo: Una alerta de TARGET_PRICE para un producto que permanece en \$34 no se volverá a alertar. Si el precio baja aún más a \$30, se emitirá una nueva alerta.

## Vistas (Seen / Unseen)
Cada alerta se rastrea individualmente y tiene una bandera de estado `seen`. Las integraciones pueden marcar alertas como leídas mediante CLI para despejar su inbox.
- Las consultas devuelven por defecto *todo* o sólo las *nuevas* `--new`.

## CLI Uso

```bash
# Listar las alertas más recientes
bin/rappi-historico alerts --top 20

# Mostrar sólo alertas no vistas
bin/rappi-historico alerts --new

# Filtrar por tipo o tienda
bin/rappi-historico alerts --type NEW_LOW --store s123

# Evaluar y buscar nuevas alertas localmente en base al dataset histórico
bin/rappi-historico alerts evaluate

# Marcar todas las alertas actuales como vistas
bin/rappi-historico alerts mark-seen
```

## Limitaciones
- Evaluaciones estrictamente locales y reactivas, sin push notifications.
- No utiliza IA ni heurísticas predictivas complejas; se fundamenta estrictamente en SQLite e historial de crawling.
