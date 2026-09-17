# Documentación

`README.md` es el punto de entrada del proyecto. Este índice contiene únicamente documentación **mantenida**; los reportes de implementación anteriores se conservan aparte como evidencia histórica.

## Usuario y operación

- [Operación](operations.md) — instalar, configurar, iniciar, actualizar, scheduler, mantenimiento, backups y recuperación.
- [Web UI](web.md) — arquitectura de interfaz y límites de seguridad.
- [CLI](cli.md) — comandos y formatos machine-readable.

## Arquitectura y dominio

- [Arquitectura](architecture.md)
- [Schema SQLite](database-schema.md)
- [Security & Privacy](security.md)
- [Price Intelligence](price-intelligence.md)
- [Normalization](product-normalization.md)
- [Product Matching](product-matching.md)
- [History](history.md)
- [Alerts](alerts.md)

La evidencia profunda de providers se conserva en `archive/provider-evidence/`; no es guía operativa vigente.

## Desarrollo

- [Development & Releases](development.md)
- [Testing](testing.md)
- [Error Handling](error-handling.md)
- [Third-party Web Assets](third-party-assets.md)
- [Experimental](experimental/README.md)

## Histórico — no usar como guía operativa

- [`archive/`](archive/) — fases, research, diagramas y guías sustituidas.
- [`audit/`](audit/) — auditorías y gates de versiones/ciclos anteriores.

Los archivos históricos se conservan para trazabilidad y contexto. **No se actualizan para reflejar el HEAD actual y no deben citarse como fuente de verdad para instalación, configuración o releases.**

Versión de código preparada para release: **v3.4.0**. Baseline pública anterior: **v3.3.1** (`9f5f3c3c12f084190d0aea8f28e4950afb51bca8`).
