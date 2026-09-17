# Contribuir a DealHunter

1. **Privacidad primero:** nunca subas DBs, logs, tokens ni coordenadas personales. Fixtures/JSON deben estar sanitizados.
2. **Entorno:** Android/Termux es el runtime primario; Python soportado y setup de desarrollo están en [`docs/development.md`](docs/development.md).
3. **Tests:** cada cambio de comportamiento necesita regresión; el gate canónico es `python -m compileall -q src tests && pytest -q` después de instalar `.[test]`.
4. **Seguridad:** no se aceptan bypasses de WAF/rate-limit, fallbacks débiles de secretos ni SQL/shell arbitrario desde la Web.
5. **Documentación:** README/`docs/operations.md` describen operación vigente. No actualices archivos de `docs/archive/` para convertirlos en fuente de verdad.
