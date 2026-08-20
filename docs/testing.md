# Testing

DealHunter se audita mediante una robusta batería de tests automatizados, diseñada no solo para validar el éxito sino escenarios de fallas y violaciones de seguridad.

Comando canónico de validación:
```bash
python3 -m compileall src bin
PYTHONPATH=src pytest
```

Estado actual v2.7.0: `180 passed, 0 failed`

## Cobertura (Categorías)
- Normalization (Métricas, conversión)
- Matching (Fingerprints, equivalencia cruzada)
- Price Intelligence (Cálculo histórico, validación temporal)
- Alerts (Deduplicación)
- Web (Rutas UI, HTMX, paginación)
- Admin (Check de red en POST, protección de secretos)
- Security (CSRF estricto, path traversal defense)
- Migrations (Esquema auto-actualizable)
