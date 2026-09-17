# CLI

El comando instalado principal es `dealhunter`. `rappi-ofertas` se conserva como alias compatible del mismo parser.

Consulta siempre la autoridad ejecutable:

```bash
dealhunter --help
dealhunter <subcomando> --help
```

## Operación principal

```bash
# Configuración y diagnóstico
dealhunter config show
dealhunter config set lat TU_LATITUD
dealhunter config set lng TU_LONGITUD
dealhunter doctor

# Web
dealhunter web --port 8765

# Providers
dealhunter sync --provider rappi
dealhunter sync --provider uber_eats
dealhunter providers
dealhunter provider uber_eats enable

# Scheduler
dealhunter scheduler enable
dealhunter scheduler status
dealhunter scheduler disable

# SQLite / operación
dealhunter db status
dealhunter db backup
dealhunter db integrity
dealhunter maintenance run

# Cuenta/membresías
dealhunter account status
dealhunter memberships
dealhunter membership uber_one active
```

## Históricos y análisis de checkout

El wrapper histórico `bin/rappi-historico` permanece por compatibilidad para análisis que aún no forman parte del parser principal instalado:

```bash
bin/rappi-historico compare "Coca Cola"
bin/rappi-historico deals --top 20
bin/rappi-historico alerts list
```

No se presenta como requisito para arrancar/operar la Web; `dealhunter web` es el comando canónico instalado.

## Salida machine-readable

`bin/rappi-historico deals --format json` y `--format csv` conservan el contrato pequeño existente:

- JSON: array de objetos; sin resultados `[]`.
- CSV: encabezados en orden de campos y una fila por resultado; sin resultados salida vacía.
- UTF-8: nombres/valores Unicode se conservan.

Los campos de negocio pertenecen a la versión de DealHunter que ejecuta la consulta. No existe un versionado paralelo de schema de salida. `table`/`markdown` son formatos humanos.

## Regla KISS

La documentación no replica todas las opciones de argparse. Si una opción cambia, `--help` es la fuente de verdad y esta página sólo conserva workflows estables.
