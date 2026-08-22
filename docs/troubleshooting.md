# Solución de Problemas (Troubleshooting)

## Limitación de Red (Rate Limiting y Cloudflare)
### HTTP 429
**Causa:** Se está consultando el endpoint `/api/pns-global-search-api/v1/unified-search` de forma sostenida (ej. sin delays o paralelizando múltiples terminales de `rappi-ofertas`).
**Solución Real:** El crawler por defecto inyecta una detención orgánica de 3 segundos entre peticiones para mitigar este efecto. Si ocurre un bloqueo de cualquier modo, la consola emitirá que el Vertical está bajo estatus `RATE_LIMITED`. Se recomienda detener la ejecución, esperar de 1 a 5 minutos, y volver a reanudar sin evadir los WAF (Web Application Firewall).

### HTTP 1015 (Cloudflare)
**Causa:** Límite de ráfagas TCP/IP que bloquea permanentemente a nivel red tu dirección externa. 
**Solución Real:** Detén de inmediato. Es un rate limit estricto a nivel de ISP/Edge. Restringe severamente el tráfico o cambia de red, pero **NO** implementes herramientas de evasión automatizada de WAF.

## Cobertura e Inventario
### "El inventario de tiendas es 0"
**Causa:** Tus coordenadas (`--lat`, `--lng`) apuntan a una zona desierta, a un mar, o un país no soportado.
**Solución Real:** Entra a Maps, recupera tu latitud/longitud decimal correcta y ponlas en los flags correspondientes.

### "No hay suficiente historial (`INSUFFICIENT_HISTORY`)"
**Causa:** Evaluaste la base de datos a instantes de crearla. `rappi-historico` requiere observar deltas de precios mínimos separados en días reales.
**Solución Real:** Simplemente espera al día siguiente.

## Problemas de Base de Datos
### `SQLite Database Locked`
**Causa:** Corriste `rappi-ofertas` o `rappi-historico` simultáneamente en varias terminales hacia el mismo archivo de base de datos.
**Solución Real:** El script actual usa conectores que confían en writes secuenciales monohilo. Cancela los procesos concurrentes y mantén un solo cron.


### DealHunter Web se congela en segundo plano (Android)
Android puede pausar DealHunter cuando Termux pasa a segundo plano.
DealHunter adquiere `termux-wake-lock` de manera automática al iniciar `bin/rappi-historico web`.
Al salir de la Web, el lock no se libera automáticamente (ya que podría ser utilizado por procesos como sshd). Usa `termux-wake-unlock` manualmente si deseas ahorrar batería y no dependes de otros procesos en segundo plano. Mantenerlo activo aumenta el consumo de batería y aún así, Android LMK/OOM podría matar Termux bajo presión de memoria.
Si el problema persiste, verifica **Admin -> Doctor** y asegúrate de deshabilitar la optimización de batería (Doze) para Termux.