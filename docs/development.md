# Development & Releases

## Entorno de desarrollo

Linux/macOS:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
```

Termux:

```bash
pkg install python python-cryptography git
python -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
```

`pyproject.toml` es la autoridad de dependencias/entry points. `requirements*.txt` sólo deben existir si aportan compatibilidad explícita; no deben convertirse en una segunda definición divergente.

## Reglas de implementación

- Lógica analítica en `src/dealhunter`; Web/CLI consumen esos servicios.
- La Web es thin layer: no duplica normalización, matching, Price Intelligence ni configuración efectiva.
- Mutaciones Web: POST + CSRF + tests.
- No servir ni persistir secrets/PII en estáticos, logs o SQLite.
- SQLite raw identity y las fronteras documentadas en `architecture.md` siguen siendo autoridad.
- `AGENTS.md` contiene reglas adicionales para agentes autónomos.

## Gate canónico

Después de instalar el paquete editable:

```bash
python -m compileall -q src tests
pytest -q
```

Antes de integrar:

```bash
git diff --check
git status --short
```

CI instala el paquete real y ejecuta la suite en Python 3.11 y 3.14. El número de tests se obtiene del SHA exacto; no se congela en documentación.

## Release

No existe necesidad demostrada de mantener un segundo artefacto binario: GitHub proporciona source archives del tag y `install.sh` instala ese checkout.

Flujo de release:

1. `develop` limpio, tests locales verdes y CI 3.11/3.14 verde.
2. Elegir versión; actualizar `dealhunter.metadata.VERSION`, CHANGELOG y referencias vigentes.
3. Validar `scripts/check_release_trace.py` y `install.sh`/`update.sh` contra el candidato.
4. Promover el SHA validado a `main` sin reescribir historia.
5. Crear tag **anotado** `vX.Y.Z` sobre ese SHA.
6. Push del tag y crear GitHub Release con notas de cambios, requisitos y migraciones relevantes.
7. Verificar que tag remoto, GitHub Release y `main` resuelvan al SHA esperado.

No se mueve un tag publicado. Un hotfix recibe una nueva versión.

## Qué no debe duplicarse en docs

- El DDL exacto: autoridad `src/dealhunter/db.py`.
- El mapa exacto de rutas Web: autoridad Flask.
- Opciones CLI: autoridad `dealhunter --help`.
- Conteos de tests: autoridad CI del SHA.
- Historia de releases: autoridad `CHANGELOG.md` + tags/GitHub Releases.
