# Testing

Instala primero el paquete con extras de test:

```bash
python -m pip install -e '.[test]'
```

Gate local canónico:

```bash
python -m compileall -q src tests
pytest -q
```

CI repite la instalación del paquete real (`pip install .` / extras de test), `pip check`, smoke de entry points/package data y la suite completa en Python 3.11 y 3.14.

El criterio es que la suite completa pase sobre el SHA exacto. El conteo no se copia a esta guía porque cambia con el proyecto.

Cobertura principal: normalización, matching, Price Intelligence, alertas, Web/Admin, seguridad, migrations, SQLite concurrency, providers, packaging y contratos CLI.
