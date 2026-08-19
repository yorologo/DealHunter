# DealHunter Web Foundation

DealHunter incorpora una interfaz web offline diseñada para funcionar localmente, sirviendo como Dashboard principal de decisiones.

## Arquitectura

Se adoptó una arquitectura **local-first** y **KISS**:
- **Backend:** Flask.
- **Frontend:** Jinja2 (server-side rendering), HTMX (búsqueda reactiva), Bootstrap 5 (UI local).
- **Domain:** Reutiliza estrictamente la lógica del dominio ya validada (v2.1-v2.5) a través de un Query Layer (`queries.py`). No se duplican cálculos.
- **Data:** SQLite, operaciones optimizadas (LIMIT, server-side queries).

## Rutas implementadas (Fase A)
- `/`: **HOME**. Dashboard real que carga nuevas alertas, oportunidades (NEW_LOW, REAL_DEAL, GOOD_PRICE) y estadísticas técnicas.
- `/search`: **Búsqueda Global**. Componente híbrido que renderiza como dropdown (HTMX via AJAX) y como página dedicada.
- Resto de rutas documentadas en la Sidebar están asignadas a un placeholder (`/deals`, `/stores`, `/admin/account`, etc).

## Responsive Design
- **Desktop:** Dispone de una Sidebar izquierda para navegación ágil y Search-bar superior.
- **Mobile (360px - 768px):** Usa un Bottom Navigation semántico que expone [Inicio, Deals, Buscar, Seguir] adaptado a pulgares. Resto del menú oculto tras Offcanvas (`☰`).
- No hay overflow horizontal.

## UX Preferences
Preferencias manejadas exclusivamente vía `localStorage`:
- **Theme:** Claro, Oscuro y Sistema (`prefers-color-scheme`).
- **Density:** Compacto (menor padding, letras pequeñas) y Confortable (defaults).

## Ejecución

```bash
bin/rappi-historico web --port 8765
```

## Limitaciones y Siguientes Fases
- Seguridad: Default `127.0.0.1`. No expone bases de datos, contraseñas ni stacks.
- Siguientes fases (Fase B): Implementar vistas de Detalle de Producto (`/products/<id>`), Comparador de Precios (`/compare`) y Exploración de Market (`/market`), conectando los flujos a datos reales.
