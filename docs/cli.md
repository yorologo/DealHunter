# CLI Reference

DealHunter provee la lógica mediante dos binarios canónicos:

## `rappi-ofertas`
Herramienta de exploración interactiva y extracciones masivas:
```bash
bin/rappi-ofertas discover --min-discount 30
bin/rappi-ofertas update
bin/rappi-ofertas doctor
bin/rappi-ofertas account status
```

## `rappi-historico`
Análisis prolongado, motor de alertas, bases de datos y servicio web:
```bash
bin/rappi-historico history
bin/rappi-historico compare
bin/rappi-historico watchlist list
bin/rappi-historico alerts evaluate
bin/rappi-historico db status
bin/rappi-historico web --port 8765
```

Utilice el flag `--help` en terminal para listar los comandos exhaustivos operativos de v2.7.0.
