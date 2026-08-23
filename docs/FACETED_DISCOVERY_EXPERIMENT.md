# Faceted Discovery + Taxonomy Experiment

**Estado:** EXPERIMENTAL (No-producción)

## 1. CRAWLER_V2_BASELINE (Adaptive Modes)

Referencia oficial extraída del snapshot de validación previa:

### NORMAL
- requests: 286
- duration: 527.83s
- merchants: 541
- observed coverage: 96.43%
- missing vs FULL: 20
- merchants/request: 1.89
- coverage_complete: 0

### DEEP
- requests: 546
- duration: 993.15s
- merchants: 556
- observed coverage: 99.10%
- missing vs FULL: 5
- merchants/request: 1.01
- coverage_complete: 0

### FULL
- requests: 676
- duration: 1237.71s
- merchants: 561
- merchants/request: 0.82

### RESIDUAL
- bottom-tier legacy parents: d, u, y, k, q
- additional requests: 130
- unique merchants contributed: 5
- marginal efficiency: ~0.038 merchants/request

### NETWORK
- 401: 0
- 403: 0
- 429: 0
- timeout: 0
- other errors: 0

### QUALITY
- tests: 314 passed / 0 failed

---

## 2. Objetivo

Investigar si las categorías, verticales y filtros estructurados de Rappi pueden:
1. mejorar la clasificación de tiendas;
2. mejorar la clasificación de productos;
3. soportar relaciones muchos-a-muchos;
4. reducir heurísticas;
5. aportar nuevas fuentes de discovery;
6. recuperar merchants residuales con menos requests.

## 3. Hipótesis Principal

Comprobar si las categorías/filtros oficiales de Rappi pueden recuperar parte o la totalidad de los 5 merchants residuales que FULL obtiene mediante 130 requests de cola larga.

## 4. Dimensiones que deben estudiarse separadamente

- vertical de comercio
- categorías de comercio
- categorías de producto
- secciones/colecciones del menú
- promociones
- atributos/filtros dinámicos

## 5. Principio de Datos

Siempre que sea posible conservar:
- `external_id`
- `raw_name`
- `normalized_name`
- `source`

**Nota:** No implementar aún schema nuevo.

## 6. Fases del Experimento

- **Fase 1:** análisis y pruebas
- **Fase 2:** aplicación y optimización
- **Fase 3:** pruebas end-to-end
- **Fase 4:** resultados
- **Fase 5:** ajustes finales

## 7. Regla KISS

Cada nueva pieza debe demostrar una mejora medible en:
- clasificación
- cobertura
- eficiencia

Si no aporta beneficio demostrable, no se incorpora.
