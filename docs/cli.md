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

La sincronización Uber normal usa Chromium headless en Termux. Carbonyl se usa
únicamente para setup o renovación del perfil; un PC no es requisito de los
runs normales.
