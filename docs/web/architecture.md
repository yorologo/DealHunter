# Web Architecture

La interfaz web de DealHunter utiliza una arquitectura *server-side rendered* (SSR) ligera, complementada con HTML hipermedia para interacciones dinámicas.

- **Backend**: Flask
- **Templating**: Jinja2
- **Dinamismo UI**: HTMX
- **Estilos**: Bootstrap 5
- **Gráficos**: Chart.js
- **Base de Datos**: SQLite

## Principio: Thin Web Layer

```text
Browser
   ↓
Flask routes
   ↓
web queries / domain services
   ↓
core DealHunter
   ↓
SQLite
```

La Web NO duplica lógicas core. Tareas como *Price Intelligence*, normalización, matching, disparadores de alertas y comprobaciones médicas residen exclusivamente en los módulos core (`src/dealhunter/*.py`), siendo la web un consumidor de estas APIs internas.

## Assets Locales

Todos los assets estáticos (CSS, JS) están servidos localmente para garantizar funcionalidad *offline-first* y máxima privacidad (sin CDNs o rastreadores).

## Navegación

```mermaid
flowchart LR
    HOME[Inicio]

    HOME --> BUY[COMPRAR]
    HOME --> INVESTIGATE[INVESTIGAR]
    HOME --> FOLLOW[SEGUIR]
    HOME --> ADMIN[ADMINISTRAR]

    BUY --> DEALS[Oportunidades]
    BUY --> MARKET[Supermercados]
    BUY --> TURBO[Turbo]
    BUY --> REST[Restaurantes]
    BUY --> CATEGORIES[Categorías]

    INVESTIGATE --> PRODUCTS[Productos]
    INVESTIGATE --> STORES[Tiendas]
    INVESTIGATE --> COMPARE[Comparador]
    INVESTIGATE --> HISTORY[Histórico]

    FOLLOW --> WATCHLIST[Watchlist (Pendiente)]
    FOLLOW --> ALERTS[Alertas (Pendiente)]

    ADMIN --> ACCOUNT[Cuenta]
    ADMIN --> RUNS[Actividad]
    ADMIN --> EVENTS[Eventos]
    ADMIN --> DOCTOR[Doctor]
    ADMIN --> DATABASE[Base de datos]
    ADMIN --> SETTINGS[Configuración]
```
