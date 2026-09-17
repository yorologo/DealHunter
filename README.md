# DealHunter

[⚡ Very Very Easy Android Quick Start](docs/VERY_EASY_QUICK_START.md) — (Recomendado para principiantes absolutos)

DealHunter es un motor local-first de inteligencia de precios y oportunidades para Rappi y Uber Eats. Su misión NO es perseguir el descuento anunciado más grande (que a menudo es engañoso o ficticio), sino **encontrar el mejor valor demostrable con datos históricos**.

## Características Principales

- **Historial de Precios**: Rastrea la evolución de precios, combatiendo inflaciones artificiales y falsos descuentos.
- **Inteligencia de Precios**: Califica las ofertas (`NEW_LOW`, `REAL_DEAL`, `GOOD_PRICE`) evaluando el precio actual contra medianas móviles de 30 días y mínimos históricos.
- **Comparación Cruzada**: Combina resultados de múltiples tiendas (`/compare`) para identificar la tienda más conveniente y el mejor precio por unidad.
- **Alertas Locales**: Evalúa caídas de precio (`PRICE_DROP`), alcance de objetivos (`TARGET_PRICE`), y restock (`BACK_IN_STOCK`) sin requerir backend cloud.
- **Arquitectura Local-first**: No envía tus datos a un backend de DealHunter y funciona con una base de datos SQLite embebida. Las credenciales de sesión sólo pueden persistirse localmente mediante el almacén seguro y con consentimiento explícito; nunca entran en SQLite, plantillas ni backups generales. Toda la interfaz web funciona offline sin CDNs.
- **Filtros Avanzados**: Permite encontrar ofertas basándose en descuento histórico en lugar de descuentos anunciados engañosos (`--new-low`, `--real-deal`).
- **Contexto Geográfico Auditable**: Cada run conserva `lat/lng`; el crawler exige una ubicación configurada y advierte cambios significativos sin borrar histórico automáticamente.
- **Navegación Nativa a Tienda**: “🛵 Abrir en Rappi” usa el deep link nativo con `store_id`, dirigido exclusivamente a `com.grability.rappi`; no tiene fallback a Home, web o navegador.
- **Arquitectura multiprovider**: adquisición productiva para Rappi y Uber Eats, con identidad raw y precios de membresía aislados por provider.

## Estado Actual

### Current development (`develop`)

- **Última release pública**: `v3.3.1` (`9f5f3c3c12f084190d0aea8f28e4950afb51bca8`).
- **Rama de integración**: `develop`, actualmente con trabajo post-`v3.3.1` del backlog A01–A32; aún no se ha decidido la siguiente versión.
- **Runtime version actual**: `3.3.1` (`dealhunter.metadata.VERSION`) hasta que exista una decisión de release validada.
- **Schema DB**: `17` (`dealhunter.db.CURRENT_SCHEMA_VERSION`).
- **Validación**: el conteo exacto se obtiene con `PYTHONPATH=src pytest -q`; no se mantiene duplicado como verdad estática.

### Última release pública

- **v3.3.1**, publicada como patch sobre v3.3.0.
- Tag `v3.3.1` → commit `9f5f3c3c12f084190d0aea8f28e4950afb51bca8`.
- La publicación se verifica con Git tag remoto + GitHub Releases; no se infiere del README.

### Estado de capacidades

| Capacidad | Estado actual del RC |
|---|---|
| Rappi acquisition | Production |
| Uber Eats acquisition | Production, phone-only |
| Provider configuration | Production |
| Membership configuration | Production |
| Product canonical infrastructure | Introduced in schema v16; matcher remains shadow/experimental |
| Commercial identity (`merchant/location`) | Schema v17 + explicit reviewed mapping workflow; unresolved listings remain `UNRESOLVED` |
| Browse taxonomy | Schema v17 + explicit reviewed mapping workflow; unmapped evidence remains `UNCLASSIFIED` |
| Large catalog pagination | Keyset/cursor in Web; legacy `page=N` links remain compatible |
| Canonical matcher | Shadow / experimental |
| Automatic canonicalization | OFF; no automatic membership write path |
| Human ground truth | Insufficient |
| Statistical identity gate | `NOT_MET` |

## Arquitectura multiprovider

- La identidad raw es siempre `(provider, store_id, product_id)`; los IDs originales nunca son reemplazados por una identidad canónica.
- Rappi y Uber Eats pueden habilitarse o deshabilitarse por separado con `provider <name> enable|disable`.
- Rappi Pro y Uber One se configuran como estados de membresía independientes con `membership <name> active|inactive|unknown`; no participan en identidad de producto.
- Uber Eats corre normalmente en el propio teléfono mediante Chromium headless nativo de Termux y CDP. No requiere PC ni servidor X durante los runs normales.
- Carbonyl se reserva para setup o renovación de la sesión/perfil. El bridge de PC es una alternativa opcional de setup, no una dependencia operativa.
- La infraestructura de producto canónico introducida en schema v16 sigue en modo shadow; no escribe membresías canónicas automáticamente.
- Schema v17 separa `merchant`, `location`, tipo de comercio y dominio de catálogo de la identidad raw del provider; no infiere estas relaciones desde nombres visibles.
- La taxonomía de navegación de DealHunter se mantiene separada de la evidencia raw del provider: sólo mappings revisados clasifican productos; lo demás permanece `UNCLASSIFIED`.

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
- Watchlist core/CLI + vista Web de solo lectura operativa.
- *Alerts Engine existente, vista UI web Parcial (Placeholder).*

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

# 3. Configurar localmente la ubicación de entrega que usa Rappi
bin/rappi-ofertas config set lat TU_LATITUD
bin/rappi-ofertas config set lng TU_LONGITUD

# 4. Capturar un baseline de esa zona
bin/rappi-ofertas discover --vertical general

# 5. Lanzar interfaz Web local
bin/rappi-historico web --port 8765
```

Abre tu navegador en `http://127.0.0.1:8765`. 

> [!NOTE]
> Por defecto, la Interfaz Web está vinculada (`bound`) a `127.0.0.1` (localhost) por razones de seguridad, y no es accesible desde otros dispositivos de la red.

> [!IMPORTANT]
> Los datos de DealHunter dependen de la ubicación. `lat/lng` viven en el `config.toml` local y no deben añadirse a Git. Cambiar de zona puede invalidar la comparabilidad del histórico; DealHunter emite un warning y conserva los datos hasta que exista una decisión explícita y un backup válido.

### Abrir una tienda en Rappi

En el Android servidor debe estar instalada la app oficial (`com.grability.rappi`) y Shizuku debe estar activo con Termux autorizado. El backend resuelve `store_id → type` en SQLite y entrega el deep link nativo `gbrappi` como Android shell. Solo están habilitados los tipos comprobados en la app instalada: Restaurants, Market, Turbo y Turbo Market.

Si el tipo, Shizuku o el Intent fallan, la operación falla cerrada: nunca abre Chrome, `rappi.com.mx` ni la pantalla Home como falso éxito. La inspección UI/OCR se limita a diagnóstico y validación manual; el crawler normal sigue usando la API estructurada y no captura precios desde la pantalla.

## Documentación

El índice completo de documentación, cubriendo arquitectura, flujos de datos, administración y uso avanzado de la CLI se encuentra en [docs/README.md](docs/README.md).

## Licencia

[MIT](LICENSE)


### Ejecución en Segundo Plano (Android)
Para mantener DealHunter Web activo en Android/Termux, DealHunter adquiere el `termux-wake-lock` automáticamente al iniciar. Nota: dado que el Wake Lock es compartido (app-wide) en Termux, DealHunter NO lo libera automáticamente al salir para no interrumpir otros procesos. Utiliza `termux-wake-unlock` manualmente cuando desees liberarlo.
- DealHunter ahora usa **Zone Inventory** si tienes sesión válida, y **Search Discovery** como fallback.

## Automated Alerts
DealHunter Phase 4I supports automated background execution and push notifications via `termux-notification`.
See [docs/SCHEDULER.md](docs/SCHEDULER.md) for instructions on setting up `cron`, configuring the DealWatcher, and managing Termux battery optimizations.

## Histórico: DealHunter v3.2.0 — Public Release Baseline

Esta versión estabiliza la infraestructura de multi-proveedor e introduce el schema v16.

### Key Features
- **A5** endpoint for primary CPG discovery with safe fallback.
- **Faceted Taxonomy** with M:N memberships (CATEGORY/COLLECTION/UNKNOWN) and structured `aisle_type` enrichment.
- **Commercial Intelligence**: **PUBLIC/PRO** separation, **Progressive**, **NxM**, and high price integrity.
- **Web Faceted Query Layer**: dynamic facets and multiselect.
- **Alerts Engine**: Temporal transitions, idempotent `alert_events`, canary Watch, and **termux-notification** delivery.
- **Operations**: Robust background **scheduler 07/10/13/19** with **flock** to prevent overlapping crawls, automatic SQLite **backup/restore**, and longitudinal validation.
- Safe **historical cutover** from v9 to v14 schemas.
