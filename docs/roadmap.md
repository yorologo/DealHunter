# Roadmap

## Completado
- **v2.1**: SQLite foundation, perfiles, historial básico.
- **v2.2**: Resilience, soporte Turbo y Restaurants, Doctor local.
- **v2.3**: Normalization engine y product matching cruzado.
- **v2.4**: Price Intelligence algorítmica robusta.
- **v2.5**: Alertas off-grid con deduplicación de SQLite.
- **v2.6**: Web UI Foundation (HTMX/Flask), componentes y gráficas locales.
- **v2.7**: Administración Web (Seguridad, Diagnostics, Settings, DB backup).
- **v2.8**: Background runtime, Wake Lock management.
- **v2.9**: Catalog Sync con sesión segura, Zone Inventory vs Search Discovery, UI/UX de Sesiones.
- **KISS Iterations**: Deal Score V1, Taxonomy, Price Integrity, Multiselect Filters, safe zone realignment.
- **v3.3.x**: Schema v17, keyset pagination, Watchlist Web de solo lectura y hardening de primer arranque/packaging Termux.
- **Develop post-v3.3.1 / A01–A10**: workflows explícitos de merchant/location y browse mapping, sorts/recency autoritativos, SecretStore atómico fail-closed y validación Admin/redirects locales.
- **Develop post-v3.3.1 / A11–A27**: queries/UX escalables, búsqueda y alertas Web, HTTP/auth reuse, retención operacional, packaging real 3.11/3.14, dependency bounds y protección mínima de ramas.
- **Develop post-v3.3.1 / A28–A32**: Bootstrap se conserva (sin migración Tailwind), `deal-score-v1` tiene corpus de regresión, contratos machine-readable CLI acotados, inventario de assets vendorizados y política de seguridad alineada con SecretStore.

## Próximo (Follow Experience)
- Mejoras incrementales de UX sobre Alertas/Watchlist existentes.
- PWA / Saved Views / Since Last Visit sólo cuando exista una necesidad demostrada.

## Futuro (Planned & Experimental)
*(Sólo funciones contempladas orgánicamente por diseño, no disponibles todavía)*
- **Planned**: PWA / Saved Views / Since Last Visit.
- **Experimental**: External retailers, Basket Optimization (calculadora combinada multicompra).
