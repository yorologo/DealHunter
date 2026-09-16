# DealHunter Scheduler Operations

DealHunter usa `cron`/`crond` en Termux y un único `flock` compartido para evitar crawls concurrentes. El scheduler gestionado por la aplicación detecta el checkout real en tiempo de ejecución; no depende de una ruta fija como `~/rappi-deal-hunter`.

## Cadencia gestionada

Los providers se escalonan para repartir carga:

- Rappi: `07:00`, `10:00`, `13:00`, `19:00`.
- Uber Eats: `07:30`, `10:30`, `13:30`, `19:30`.

La zona horaria es la zona local efectiva de Termux.

Cada job ejecuta `bin/rappi-ofertas sync --provider <provider>` y, sólo si el sync termina correctamente, `bin/dealwatcher`. Ambos providers comparten `${TMPDIR}/dealhunter.lock` mediante el `flock` encontrado en el entorno.

## Prerrequisitos obligatorios

Antes de habilitar el scheduler:

1. configura `lat` y `lng` en `~/.config/dealhunter/config.toml` mediante `bin/rappi-ofertas config set lat ...` y `config set lng ...`;
2. verifica `bin/rappi-ofertas doctor`;
3. confirma que los providers deseados estén habilitados;
4. inicia `crond` y, si necesitas ejecución puntual con pantalla apagada, adquiere `termux-wake-lock`.

DealHunter falla cerrado si la ubicación no está configurada. No existe fallback de ciudad o coordenadas hardcodeadas.

## Habilitar / deshabilitar

La interfaz Admin de Catalog Sync usa `dealhunter.scheduler.enable_scheduler()` / `disable_scheduler()`. El gestor:

- conserva líneas de cron ajenas a DealHunter;
- elimina entradas legacy gestionadas por DealHunter;
- instala exactamente las líneas Rappi/Uber actuales;
- verifica el `crontab` mediante lectura posterior exacta;
- crea el directorio local de logs si hace falta.

Para auditar el resultado efectivo:

```bash
crontab -l
```

No copies rutas absolutas de otro checkout. Si mueves el repositorio, vuelve a habilitar el scheduler para regenerar los comandos desde la ruta real.

## Wake-lock / Doze

Android puede suspender Termux cuando la pantalla está apagada. En un dispositivo dedicado, ejecuta manualmente:

```bash
termux-wake-lock
```

El wake-lock es global para Termux; no debe liberarse automáticamente por un proceso individual. Cuando ya no necesites servicios Termux en segundo plano:

```bash
termux-wake-unlock
```

## Estado y logs

- Jobs efectivos: `crontab -l`.
- Lock: `${TMPDIR}/dealhunter.lock` (resuelto por Python con `tempfile.gettempdir()`).
- Log: `<checkout>/logs/crawler-cron.log`.
- DB: `RAPPI_DB_PATH` si está definido; en instalaciones legacy se conserva una DB existente en `~/rappi-deal-hunter/rappi-deals.db`; de lo contrario se usa `${XDG_DATA_HOME:-~/.local/share}/dealhunter/rappi-deals.db`.

## Fallos

Un job que no puede adquirir `flock` no inicia un segundo crawler. Un fallo del sync impide ejecutar `dealwatcher` en ese job. Los fallos de entrega de notificaciones se registran sin convertir datos parciales en éxito ni corromper observaciones históricas.
