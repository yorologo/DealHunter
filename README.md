# DealHunter

DealHunter es un motor local-first de inteligencia de precios y oportunidades orientado inicialmente a Rappi. Su misión NO es perseguir el descuento anunciado más grande (que a menudo es engañoso o ficticio), sino **encontrar el mejor valor demostrable con datos históricos**.

## Características Principales

- **Historial de Precios**: Rastrea la evolución de precios, combatiendo inflaciones artificiales y falsos descuentos.
- **Inteligencia de Precios**: Califica las ofertas (`NEW_LOW`, `REAL_DEAL`, `GOOD_PRICE`) evaluando el precio actual contra medianas móviles de 30 días y mínimos históricos.
- **Comparación Cruzada**: Combina resultados de múltiples tiendas (`/compare`) para identificar la tienda más conveniente y el mejor precio por unidad.
- **Alertas Locales**: Evalúa caídas de precio (`PRICE_DROP`), alcance de objetivos (`TARGET_PRICE`), y restock (`BACK_IN_STOCK`) sin requerir backend cloud.
- **Arquitectura Local-first**: No envía tus datos a servidores externos, no guarda configuraciones de cuenta confidenciales y funciona con una base de datos SQLite embebida. Toda su interfaz web funciona offline sin CDNs.
- **Filtros Avanzados**: Permite encontrar ofertas basándose en descuento histórico en lugar de descuentos anunciados engañosos (`--new-low`, `--real-deal`).
- **Contexto Geográfico Auditable**: Cada run conserva `lat/lng`; el crawler exige una ubicación configurada y advierte cambios significativos sin borrar histórico automáticamente.
- **Navegación Nativa a Tienda**: “🛵 Abrir en Rappi” usa el deep link nativo con `store_id`, dirigido exclusivamente a `com.grability.rappi`; no tiene fallback a Home, web o navegador.

## Estado Actual

- **Versión**: `v2.8.0`
- **Schema DB**: `7`
- **Tests**: `227 passed`
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
- *Watchlist core/CLI existente, vista UI web Parcial (Placeholder).*
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