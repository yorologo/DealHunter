# Interfaz de Línea de Comandos (CLI)

Existen dos binarios principales: el minero y el auditor de ofertas.

## 1. `rappi-ofertas`
El motor principal de peticiones a la Search API y volcado de base de datos.

### Uso
```bash
./bin/rappi-ofertas [--vertical VERTICAL] [--lat LAT] [--lng LNG]
```

### Argumentos Reales
* `--vertical` (str, opcional): Limita o amplía los diccionarios semilla de rastreo para evitar que alimentos dominen sobre mascotas o electrónica. Valores posibles: `general` (barre todos secuencialmente), `supermercado`, `farmacia`, `mascotas`, `bebe`, `higiene`, `hogar`, `tecnologia`. (Default: `general`).
* `--lat` (float, opcional): Latitud geográfica del punto central de escaneo. (Default: 19.4326).
* `--lng` (float, opcional): Longitud geográfica. (Default: -99.1332).
* `--test` (flag, opcional): Ejecuta el vertical restringido `test_run` para validar funcionalidad técnica o DB bindings sin provocar escaneos mayores.

---

## 2. `rappi-historico`
Consume la base de datos local pre-rastreada para auditar precios sin conectarse a internet.

### Uso
```bash
./bin/rappi-historico [--min-history-days N] [--top N] [--json]
```

### Argumentos Reales
* `--min-history-days` (float, opcional): Exigencia de maduración de la data antes de emitir dictamen matemático (evita validar ofertas dudosas de primer día). (Default: `1.0`).
* `--store` (str, opcional): Filtra el motor por un `store_id` específico.
* `--product` (str, opcional): Filtra un producto exacto a evaluar.
* `--top` (int, opcional): Número máximo de ofertas reales a imprimir en la tabla estándar output. (Default: `50`).
* `--json` (flag, opcional): Enmudece la salida tabular humana y deja todo impreso en `history-analysis.json`.
