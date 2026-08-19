# DealHunter

Herramienta de recolección, normalización y análisis histórico de precios y promociones.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **DealHunter** consulta de forma autónoma el catálogo de tiendas disponibles en tu área, audita matemáticamente las promociones presentadas y construye un historial SQLite para evidenciar caídas reales de precio y aislar las falsas promociones.

---

## ¿Qué es DealHunter?
DealHunter es un motor CLI escrito en Python, diseñado para ejecutarse localmente (idealmente en Termux para Android) que:
1. Rastrea el catálogo público por zonas (General, Supermercado, Farmacia, etc).
2. Estructura y desambigua matemáticamente los descuentos (diferencia un 2x1 de un descuento directo).
3. Acumula las observaciones en una base de datos SQLite para combatir la manipulación de "precios de lista".

## ¿Qué problema resuelve?
Las plataformas de delivery suelen alterar el "Precio Original" antes de aplicar un descuento, o encimar etiquetas de "2x1" que realmente no son rebajas. DealHunter descubre el catálogo "invisible", normaliza las matemáticas de las promociones y mantiene un registro estricto a través de los días para revelarte el verdadero *Mínimo Histórico*.

## Características
* **Búsqueda Estructurada:** API nativa sin depender de OCR ni Accessibility Services.
* **Cobertura Adaptativa:** Detecta tiendas con poco inventario ("huecos") y las inyecta como *keywords* para forzar su aparición.
* **Deduplicación Automática:** Filtra observaciones repetidas por corrida.
* **Motor Matemático (Discount Engine):** Descifra promociones NxM (2x1, 3x2) vs Descuento Directo.
* **Histórico Offline:** SQLite append-only local.
* **Analizador Analítico:** Computa medianas a 7 y 30 días, declarando ofertas irrebatibles (`NEW_LOW`, `REAL_DEAL`).
* **Errores Estructurados:** Códigos de error claros con acciones recomendadas.
* **Runs Parciales:** Los datos ya recolectados sobreviven interrupciones.
* **Doctor:** Diagnóstico del sistema con `rappi-ofertas doctor`.
* **Rappi Turbo:** Integración nativa como vertical con análisis histórico de precios.
* **Restaurantes:** Soporte inicial para menús, platillos y sus promociones (`rappi-ofertas restaurants`).
* **Privacidad y Diagnósticos:** Verificación read-only y sanitizada del estatus de la cuenta de usuario.
  > Authentication tokens are ephemeral and are never persisted by DealHunter.

## Cómo funciona
```text
DealHunter consulta productos disponibles
        ↓
normaliza precios y promociones
        ↓
detecta descuentos reales (evita sumar 3x2 + rebaja)
        ↓
elimina duplicados intra-corrida
        ↓
guarda observaciones (SQLite)
        ↓
construye histórico a través de ejecuciones diarias
        ↓
ordena las mejores ofertas basándose en estadísticas (no en marketing)
```

## Instalación rápida
Desde tu terminal en Linux o Termux (Android):
```bash
pkg update && pkg install git python sqlite
git clone git@github.com:yorologo/DealHunter.git
cd DealHunter
chmod +x bin/rappi-ofertas bin/rappi-historico
```

## Primera ejecución
Ubica una latitud y longitud pública cercana a ti (ejemplo, el Zócalo de CDMX).
```bash
./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical general
```

## Documentación
El proyecto está completamente documentado para tres perfiles (Básico, Avanzado y Desarrollador):
* [Primeros Pasos (Tutorial)](docs/getting-started.md)
* [Ejemplos Prácticos](docs/examples.md)
* [Casos de Uso](docs/use-cases.md)
* [Motor de Descuentos](docs/discount-engine.md)
* [Análisis Histórico](docs/historical-analysis.md)
* [Arquitectura y Diagramas](docs/diagrams/architecture.md)
* [Glosario](docs/glossary.md)
* [FAQ](docs/faq.md)
* [Troubleshooting](docs/troubleshooting.md)
* [Roadmap](docs/roadmap.md)

## Contribuir
Por favor revisa [CONTRIBUTING.md](CONTRIBUTING.md) antes de enviar un Pull Request. Las bases de datos reales y la PII (Personal Identifiable Information) están estrictamente prohibidas en el repositorio.

## Licencia
[MIT](LICENSE)

## Disclaimer
Proyecto de uso personal, analítico y offline. No afiliado con Rappi. La herramienta es estrictamente *read-only* y no evade controles de autenticación. Úsela bajo su propio riesgo y respetando los términos de servicio aplicables.

## Novedades v2.3 (En Desarrollo)
- **Normalización de Productos:** Extracción estructurada de marcas, cantidades y unidades (`g`, `kg`, `ml`, `L`, `piezas`, `packs`).
- **Precio Unitario:** Cálculo dinámico de `UNIT_PRICE` (ej. $90/L) para comparativas justas.
- **Product Matching:** Identificación conservadora de productos equivalentes a través de tiendas (`EXACT_MATCH`, `HIGH_CONFIDENCE_MATCH` y `FUZZY_MATCH` como fallback).
- **Comparación Cross-Store:** Nuevo comando `bin/rappi-historico compare` para hallar el mejor precio (y diferencia porcentual) del mismo producto.
- **Sorting CLI:** Soporte para ordenar resultados por precio unitario (`--sort unit-price`).
- **Error Recovery:** Tolerancia a fallos por cantidad ambigua/desconocida (preserva raw data).
