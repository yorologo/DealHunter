# Ejemplos de Uso

DealHunter utiliza una CLI muy predecible. Aquí tienes ejemplos prácticos. Todos los datos generados son locales.

## Caso 1 — Buscar mejores ofertas cercanas
**Objetivo:** Obtener las promociones del área general predefinida por las *seed keywords* de todos los verticales.
**Comando:**
```bash
./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical general
```
**Qué hace:** Itera desde supermercados hasta tiendas de tecnología y mascotas, llenando tu base de datos y deteniéndose automáticamente cuando nota que la búsqueda ya no trae productos nuevos.

## Caso 2 — Sólo supermercado
**Objetivo:** Ignorar medicinas y croquetas para enfocarte sólo en tu despensa.
**Comando:**
```bash
./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical supermercado
```

## Caso 3 — Farmacias
**Objetivo:** Buscar promociones de temporada en medicamentos.
**Comando:**
```bash
./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical farmacia
```

## Caso 4 — Tecnología
**Objetivo:** Encontrar remates de cables, memorias o periféricos en tiendas MacStore, Lumen o Steren cercanas.
**Comando:**
```bash
./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical tecnologia
```

## Caso 5 — Mascotas
**Objetivo:** Rastrear alimento en tiendas como Petco o Maskota.
**Comando:**
```bash
./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical mascotas
```

## Caso 10 — Consultar histórico
**Objetivo:** Auditar todas las ofertas que recolectaste hoy contra las del resto del mes.
**Comando:**
```bash
./bin/rappi-historico
```
**Salida esperada:** Una tabla donde la columna `ESTADO` clasificará qué tan buena es la oferta (ej. `REAL_DEAL`, `NEW_LOW`). Si es tu primer día, saldrá `INSUFFICIENT_HISTORY`.

## Caso 13 — Automatización diaria opcional (Termux Cron)
Para obtener el máximo valor de DealHunter (como identificar el `NEW_LOW` o mejores ofertas), es recomendable construir un histórico periódico de los productos de tu zona. Una estrategia efectiva es configurar capturas automáticas en horarios donde Rappi suele actualizar promociones o donde tienes mayor intención de compra (ej: desayuno, comida, cena). 

Esta automatización es **100% opcional**. 

En Termux puedes instalar el paquete de cron y configurarlo:
```bash
# Instalar cron
pkg install cronie

# Iniciar el servicio (puedes agregar este comando a tu ~/.bashrc para que inicie con Termux)
crond

# Editar las tareas programadas
crontab -e
```

Agrega una línea para correr tu escaneo, por ejemplo a las 07:00, 10:00, 13:00 y 19:00 todos los días:
```cron
0 7,10,13,19 * * * cd /data/data/com.termux/files/home/rappi-deal-hunter && ./bin/rappi-ofertas discover --lat TU_LATITUD --lng TU_LONGITUD --vertical general >> logs/crawler-cron.log 2>&1
```

Estos horarios no son intervalos uniformes. Están pensados para capturar:
- **07:00** — Inicio del día (promociones matutinas, restock).
- **10:00** — Media mañana (catálogo estabilizado).
- **13:00** — Comida (peak de demanda y cambios de precio).
- **19:00** — Cena / prime time (máxima actividad de usuarios).

> **Nota:** `crond` debe estar corriendo para que las tareas se ejecuten. En Android, las restricciones de batería pueden detener Termux en segundo plano. Considera usar `termux-wake-lock` para mantener la sesión activa, y revisa las opciones de tu dispositivo para excluir Termux de la optimización de batería.
