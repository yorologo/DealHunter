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

## Caso 13 — Automatización diaria (Termux Cron)
Para obtener valor real del histórico, necesitas ejecutar DealHunter todos los días. En Termux puedes instalar `cron`:
```bash
pkg install cronie
crond
crontab -e
```
Agrega una línea para correr tu escaneo a las 10:00 AM todos los días (suponiendo que estés en la raíz del proyecto):
```text
0 10 * * * cd /data/data/com.termux/files/home/DealHunter && ./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical general > logs/cron.log 2>&1
```
