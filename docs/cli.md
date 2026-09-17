# CLI Reference

DealHunter provee la lógica mediante dos binarios canónicos:

## `rappi-ofertas`
Herramienta de exploración interactiva y extracciones masivas:
```bash
bin/rappi-ofertas discover --min-discount 30
bin/rappi-ofertas update
bin/rappi-ofertas doctor
bin/rappi-ofertas account status
bin/rappi-ofertas providers
bin/rappi-ofertas provider uber_eats enable
bin/rappi-ofertas memberships
bin/rappi-ofertas membership uber_one active
bin/rappi-ofertas sync --provider uber_eats --lat TU_LAT --lng TU_LNG
```

## `rappi-historico`
Análisis histórico, comparación, motor de alertas y servicio web:
```bash
bin/rappi-historico compare "Coca Cola"
bin/rappi-historico deals --top 20
bin/rappi-historico alerts list
bin/rappi-historico alerts evaluate
bin/rappi-historico web --port 8765
```

Watchlist y administración de SQLite pertenecen a `rappi-ofertas`:
```bash
bin/rappi-ofertas watch list
bin/rappi-ofertas db status
```

Utilice `--help` para consultar los comandos que expone el HEAD instalado. La
descripción de la CLI obtiene su versión de `dealhunter.metadata.VERSION`.

### Salida machine-readable

`rappi-historico deals --format json` y `--format csv` son interfaces CLI
públicas para automatización local. El contrato deliberadamente pequeño es:

- JSON: un array de objetos, preservando los nombres y valores entregados por la
  consulta de `deals`; sin resultados produce `[]`.
- CSV: encabezados en el mismo orden de campos de la consulta y una fila por
  resultado; sin resultados produce salida vacía.
- UTF-8: los nombres y valores Unicode se conservan.

Los campos de negocio pertenecen a la versión de DealHunter que ejecuta la
consulta; no existe un segundo versionado de schema de salida mientras no haya
un API externo independiente que lo requiera. `table` y `markdown` son formatos
humanos y no se tratan como contratos machine-readable.

La sincronización Uber normal usa Chromium headless en Termux. Carbonyl se usa
únicamente para setup o renovación del perfil; un PC no es requisito de los
runs normales.
