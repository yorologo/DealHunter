# Alerts Engine

El motor local evalúa cambios relevantes entre runs sin infraestructura cloud. La autoridad ejecutable está en `src/dealhunter/alerts.py` / `alert_events`.

## Eventos

- `TARGET_PRICE`: alcanza el umbral de Watchlist.
- `NEW_LOW`: nuevo mínimo histórico.
- `REAL_DEAL`: evidencia histórica fuerte.
- `PRICE_DROP`: caída entre observaciones.
- `BACK_IN_STOCK`: retorno después de ausencia confirmada.

## Invariantes

1. **Incremental**: evalúa el alcance afectado por el run.
2. **Partial-run safe**: un run incompleto no inventa desapariciones en tiendas no cubiertas.
3. **Snapshot completeness**: ausencia sólo es evidencia negativa cuando la cobertura aplicable fue completa.
4. **Canales separados**: precio público y de membresía no se mezclan silenciosamente.
5. **Idempotencia**: re-evaluar el mismo run no duplica eventos.

La Web `/alerts` es una vista local de sólo lectura sobre este motor. La entrega Android puede usar DealWatcher/Termux:API cuando está disponible; una falla de notificación no debe romper el crawler.
