# Testing

DealHunter se audita mediante una robusta batería de tests automatizados, diseñada no solo para validar el éxito sino escenarios de fallas y violaciones de seguridad.

Comando canónico de validación:
```bash
python -m compileall -q src tests
PYTHONPATH=src pytest tests -q
```

El criterio actual es que la suite completa pase. El conteo se obtiene de la
ejecución/CI del HEAD exacto y no se duplica en este documento.

## Cobertura (Categorías)
- Normalization (Métricas, conversión)
- Matching (Fingerprints, equivalencia cruzada)
- Price Intelligence (Cálculo histórico, validación temporal)
- Alerts (Deduplicación)
- Web (Rutas UI, HTMX, paginación)
- Admin (Check de red en POST, protección de secretos)
- Security (CSRF estricto, path traversal defense)
- Migrations (Esquema auto-actualizable)
