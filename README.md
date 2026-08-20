# DealHunter

DealHunter es un motor local-first de inteligencia de precios y oportunidades orientado inicialmente a Rappi. Su misión NO es perseguir el descuento anunciado más grande (que a menudo es engañoso o ficticio), sino **encontrar el mejor valor demostrable con datos históricos**.

## Características Principales

- **Historial de Precios**: Rastrea la evolución de precios, combatiendo inflaciones artificiales y falsos descuentos.
- **Inteligencia de Precios**: Califica las ofertas (`NEW_LOW`, `REAL_DEAL`, `GOOD_PRICE`) evaluando el precio actual contra medianas móviles de 30 días y mínimos históricos.
- **Comparación Cruzada**: Combina resultados de múltiples tiendas (`/compare`) para identificar la tienda más conveniente y el mejor precio por unidad.
- **Alertas Locales**: Evalúa caídas de precio (`PRICE_DROP`), alcance de objetivos (`TARGET_PRICE`), y restock (`BACK_IN_STOCK`) sin requerir backend cloud.
- **Arquitectura Local-first**: No envía tus datos a servidores externos, no guarda configuraciones de cuenta confidenciales y funciona con una base de datos SQLite embebida. Toda su interfaz web funciona offline sin CDNs.
- **Filtros Avanzados**: Permite encontrar ofertas basándose en descuento histórico en lugar de descuentos anunciados engañosos (`--new-low`, `--real-deal`).

## Estado Actual

- **Versión**: `v2.7.0`
- **Schema DB**: `7`
- **Tests**: `180 passed`
- **Integración API**: 0 endpoints bloqueados, fallback local en diagnósticos.

### Experiencia Web

DealHunter incluye una Interfaz Web responsiva (UI/UX) para navegar ofertas sin usar la terminal:

#### COMPRAR
- Inicio
- Oportunidades
- Supermercados
- Turbo
- Restaurantes
- Categorías
- Tiendas

#### INVESTIGAR
- Productos
- Product Detail
- Histórico
- Comparador
- Búsqueda global

#### SEGUIR
- *Watchlist core/CLI existente, vista UI web Próximamente.*
- *Alerts Engine existente, vista UI web Próximamente.*

#### ADMINISTRAR
- Admin Home
- Cuenta
- Runs
- Events/Errors
- Doctor
- Database
- Backup
- Settings

## Quick Start

```bash
# 1. Clonar el repositorio
git clone git@github.com:yorologo/DealHunter.git
cd DealHunter

# 2. Explorar CLI
bin/rappi-historico --help
bin/rappi-ofertas --help
bin/rappi-ofertas doctor --help
bin/rappi-ofertas account --help

# 3. Lanzar interfaz Web local
bin/rappi-historico web --port 8765
```

Abre tu navegador en `http://127.0.0.1:8765`. 

> [!NOTE]
> Por defecto, la Interfaz Web está vinculada (`bound`) a `127.0.0.1` (localhost) por razones de seguridad, y no es accesible desde otros dispositivos de la red.

## Documentación

El índice completo de documentación, cubriendo arquitectura, flujos de datos, administración y uso avanzado de la CLI se encuentra en [docs/README.md](docs/README.md).

## Licencia

[MIT](LICENSE)
