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

## Phase 2A - Offline Control Application

- **Bug Corregido:** La función recursiva `extract_products` en `catalog_sync.py` detectaba el nombre de los `corridors`/`aisles` padre pero descartaba la variable inmediatamente al descender por los nodos hijos, causando que miles de productos perdieran su contexto jerárquico.
- **Jerarquía Preservada:** Se modificó la firma para aceptar `ancestors`, propagando el _path_ completo hasta el nodo del producto. La nueva propiedad `memberships` en el diccionario del producto almacena múltiples ancestros (incluyendo nombre, ID original, tipo y ruta completa).
- **Multi-pertenencia:** Se corrigió la deduplicación de diccionarios que pisaba el producto completo. Ahora el producto único por ID preserva la suma de todas sus membresías si aparece en más de un contenedor (e.g. en la categoría regular y en "Promociones").
- **No Integrado Aún:** El crawler no inserta todavía estas `memberships` en la base de datos real. El schema permanece intacto.
- **Compatibilidad Legacy:** La lógica de extracción anterior para asignar `p["category"]` fue dejada intacta como compatibilidad legacy en `extract_products`.
- **Limitaciones de Medición Offline:** Ya que los diccionarios JSON `__NEXT_DATA__` no se persisten en el sistema local después del crawler, el número exacto de categorías que podrán ser inyectadas permanece UNKNOWN hasta que se realice el _crawl_ real, pero la estructura ahora lo permite de forma demostrada en las pruebas.

## Phase 2B — Single-store live observation

- **Store Utilizada:** VELMA BOX (store_id: 1923782439)
- **Request Count:** 1 a `unified-search`, 1 a `tiendas/` (`__NEXT_DATA__`). Límite respetado rigurosamente.
- **Evidencia sobre Nivel A/B:**
  - Nivel A (`parent_store_type`) llegó como `restaurants`.
  - Nivel B (Subcategorías) llegó como `"categories": "Sushi · China"` en `unified-search`, y como el array `"tags": ["Sushi", "China"]` en `__NEXT_DATA__`.
- **Estructuras Reales Observadas:** Todos los agrupadores ("Sushi", "Bebidas", pero también productos sueltos promocionados como "Morita Roll") llegaron en el mismo array plano `"corridors"`, con `type="corridor"`. No existe discriminador estructural (flag) nativo que separe "colecciones/promociones" de "taxonomía pura".
- **Evidencia de Multi-pertenencia:** Al menos 3 productos ("Eby don", "Zu-sushi hot", "Cheese ball") pertenecen simultáneamente a un _corridor_ con su mismo nombre y al _corridor_ "Especialidades".
- **Resultado del Golden Check:** "California especial" y "Sushi del mes" están **presentes**. Ambos mantienen el precio de oferta (63 de 210, y 150 de 300), demostrando descuentos reales del 70% y 50% extraídos y aislados correctamente de la taxonomía. Ninguno tenía campo "category"; dependían puramente de su membresía al _corridor_ "Sushi".
- **Limitaciones:** Este payload específico de restaurante no poseía _corridors_ llamados explícitamente "Populares" o "Descuentos", aunque expuso productos sueltos como pasillos que funcionalmente actúan como colecciones destacadas.


## Phase 2C — Cross-vertical Taxonomy Validation

- **Muestras:** City Market (Supermarket), Turbo (Turbo), Farmacias Benavides (Pharmacy).
- **Nivel A (Vertical):** El campo `parent_store_type` está sucio (ej. Farmacias es "Farmatodo", Turbo es "chiper_home"). Sin embargo, `vertical_sub_group` demostró ser una señal limpia y universal ("restaurants", "Market", "Turbo", "Farmacia").
- **Nivel B (Store Subcategories):** Sólo los restaurantes incluyen esta información nativa (ej. "Sushi · China"). Supermercados y Farmacias retornan nulo.
- **Jerarquía y Multi-pertenencia:** Validado generalizable. En Turbo, 14 de 88 productos (15.9%) presentaron multi-pertenencia explícita en el JSON (ej. `['¡Licores y botanas en 10min!', 'Ofertas', 'Botanas']`).
- **Señales de Colección vs Taxonomía:** **Estructuralmente idénticos**. En el payload de Turbo CPG, contenedores como "Ofertas" (colección) y "Botanas" (taxonomía) son nodos hermanos con idénticas propiedades (`parent_id: 0`, `icon`, `product_count`). 
- **Conclusión Semántica:** Las heurísticas de nombre (diccionarios, regex, NLP) serán **obligatorias** para poder separar colecciones comerciales de clasificaciones reales, ya que Rappi no expone una bandera (flag) diferencial en el JSON de catálogo.

## Phase 3A — RAW faceted persistence

- **Schema introducido:** Se actualizó `schema_version` a 10. Se agregó la columna `vertical` a `stores`. Se crearon las tablas `store_facets` (para subcategorías de sucursal) y `product_memberships` (para herencia N:M de productos).
- **Fuente de Vertical:** Se extrae de `vertical_sub_group` (o `parent_store_type` como fallback), normalizando a `Restaurantes`, `Supermercado`, `Turbo` o `Farmacia`.
- **Store Facets:** Se unifican `categories` (string "·") y `tags` (array) deduplicados en `store_facets`.
- **Product Memberships:** Cada contenedor padre del JSON `__NEXT_DATA__` visitado se guarda asociando el producto al pasillo. Se incluye el `path` como JSON.
- **Reconciliación y Partial-run safety:** Se insertan vía `INSERT ... ON CONFLICT DO UPDATE SET last_seen=excluded.last_seen`. No se borran datos masivamente, protegiendo contra timeouts y ejecuciones parciales.
- **Compatibilidad Legacy:** `stores.type`, `products.category` y `products.category_source` continúan operando idéntico (sin alteraciones), evitando romper queries existentes o lógicas web.
- **Lo que sigue sin clasificarse:** "Ofertas", "Populares" y otros contenedores entran crudos a la DB sin un flag semántico de colección.

## Phase 3A.1 — Safe Facet Reconciliation

- **Reconciliación de Product Memberships:** En observaciones completas de un producto, las membresías que ya no aparecen en el payload se eliminan de `product_memberships`. Si un run es parcial o el producto no se observa, se conservan todas sus membresías históricas.
- **Reconciliación de Store Facets:** En observaciones de tiendas, si el payload incluye los campos `tags` o `categories` pero ya no contienen ciertos valores, dichos valores se eliminan. Si el payload omite completamente esos metadatos, los facets históricos se conservan por seguridad.
- **Mecanismo KISS:** Se utilizó `last_seen != now` en el ciclo de persistencia para eliminar las relaciones caducadas sin necesidad de añadir versionado complejo ni alterar el `schema_version` (10).

## Phase 3A.2 — CPG RAW membership completeness

- **Diferencia Restaurants vs CPG:** Los restaurantes estructuran sus membresías mediante diccionarios explícitos de tipo "corridor". Los CPG (Supermercado, Turbo, Farmacia) carecen de `type` semántico en el JSON, empleando contenedores jerárquicos basados en `parent_id`, `aisle_id` y atributos `products`/`items`.
- **Estructura soportada:** Se amplió `extract_products()` para identificar nodos CPG que posean un `name` y al menos un indicador de membresía (`parent_id`, `aisle_id`, `products` o `items`). 
- **Comportamiento de parent_id/aisle_id:** `parent_id: 0` se trata correctamente como nodo raíz, sin crear un ancestro fantasma "0". Cualquier nodo CPG válido agrega su "name" al path de los productos descendientes y extrae su ID real (sea `id`, `corridor_id` o `aisle_id`).
- **Ausencia de clasificación semántica:** Los nodos CPG capturados heredan `raw_type: "unknown"` en la persistencia RAW, dado que Rappi no expone un tag diferenciador en el JSON para estos comercios.
- **Compatibilidad Legacy:** No se modificaron esquemas, heurísticas ni la estructura principal del pipeline. La multi-pertenencia para CPG ahora viaja idéntica a la de Restaurants.

## Phase 3B — Conservative semantic classifier

- **Tres Estados Semánticos:** Un `product_membership` RAW puede clasificarse como `CATEGORY`, `COLLECTION` o `UNKNOWN`. La prioridad es la precisión, delegando a `UNKNOWN` cualquier caso dudoso.
- **Fuentes de Evidencia para CATEGORY:** Se considera `CATEGORY` si existe coincidencia exacta (tras normalizar espacios y mayúsculas) entre el nombre del membership y la categoría proporcionada por Rappi (`products.category` cuando `category_source = 'provider'`). No se confía en las categorías inferidas legacy.
- **Fuentes de Evidencia para COLLECTION:** Se considera `COLLECTION` si el nombre normalizado coincide exactamente con un diccionario estricto de colecciones demostradas: *Promos, Ofertas, Descuentos, Populares, Destacados, Last Chance, Last Chance Deals, Ofertas Pro*. No se emplean regex amplias.
- **UNKNOWN intencional:** Contenedores homónimos (ej. "Morita Roll"), contenedores de un solo producto, y cualquier contenedor que no tenga evidencia fuerte caen en `UNKNOWN`. "unknown" es también el `raw_type` base para la ingesta CPG, el cual no influye en la semántica.
- **Precedencia:** Si un contenedor coincide simultáneamente como categoría de proveedor y como colección conocida, el conflicto se resuelve devolviendo `UNKNOWN`.
- **Persistencia:** No se persistió semántica. El código de la Fase 3B es puramente validación in-memory (`src/dealhunter/semantic.py`). Todo el esquema permanece inalterado.

## Phase 3C — Real-data shadow semantic validation

- **Ejecución:** Se analizaron offline 4 sucursales (Velma Box, City Market, Turbo, Farmacias Benavides) extrayendo 314 productos y 405 memberships RAW en una base de datos temporal, consumiendo solo 4 requests.
- **Precisión:** De 405 memberships, el clasificador identificó 15 como `CATEGORY` (ej. "Cervezas", corroboradas contra el proveedor) y 30 como `COLLECTION` (ej. "Ofertas"). 360 cayeron en `UNKNOWN`.
- **UNKNOWNs de Restaurantes:** Para Velma Box, términos como "Sushi" cayeron en `UNKNOWN` intencionalmente, debido a que el producto tenía la categoría `Sushi` pero provenía de `inferred` (heurística antigua). Esto valida la postura restrictiva de no usar inferencias antiguas como ground truth.
- **Colecciones útiles:** La etiqueta "Ofertas" apareció en 30 memberships, validando el diccionario restrictivo.
- **Falsos positivos (Sanity check):** Las 15 clasificaciones a CATEGORY provinieron de coincidencias perfectas ("Cervezas") avaladas por el proveedor (`provider`), cumpliendo al 100% el contrato.
- **Estado de Schema:** El schema se mantuvo en v10 sin inyectar las clasificaciones. El clasificador es un filtro puramente lógico y confiable para su eventual despliegue masivo.

## Phase 3C.1 — Membership boundary correction

- **Bug detectado en Phase 3C:** El objeto raíz JSON del comercio (que incluye su nombre y arrays como `corridors` o `components`) estaba evaluándose accidentalmente como `is_container = True`. Esto provocó que pseudo-memberships como "VELMA BOX ZAPOPAN - Lomas de Zapopan" se anexaran a la taxonomía de los productos (multi-membership artificial masivo).
- **Causa:** La generalización del reconocimiento jerárquico CPG en Phase 3A.2 aceptaba a cualquier nodo con "name" y descendientes como contenedor taxonómico.
- **Corrección Estructural:** En lugar de aplicar heurísticas sobre el nombre o bloqueos duros de IDs (que podrían fallar), se introdujo el concepto posicional de `is_root=True` (top-level document payload) dentro del recorrido recursivo `extract_products`.
- **Efecto:** El documento raíz que inicia el parseo nunca se considera un contenedor taxonómico, mientras que cualquier contenedor interno (tenga tipo CPG implícito o explícito de Restaurants, o incluso `parent_id=0`) es procesado y propagado correctamente hacia `memberships`.

## Phase 3C.2 — Single-store post-fix validation

- **Validación Exitosa:** Se ejecutó una prueba empírica puntual sobre VELMA BOX ZAPOPAN (1923782439) consumiendo solo 1 petición HTTP al menú.
- **Root regression eliminada:** La contaminación masiva desapareció. El nombre de la sucursal ("VELMA BOX ZAPOPAN - Lomas de Zapopan") bajó a 0 ocurrencias dentro de `memberships`.
- **Memberships RAW preservados:** Se detectaron 66 taxonomías válidas (ej. "Sushi", "Especialidades", "Bebidas", "Postres").
- **Golden Check:** "California especial" y "Sushi del mes" demostraron heredar limpiamente `["Sushi"]` como membresía, como era esperado estructuralmente.
- **Corrección final de boundary:** Debido a que Next.js anida el store context, en lugar de confiar solo en un booleano `is_root=True` posicional, la función `is_container` ahora bloquea activamente a cualquier nodo con firmas estructurales de wrapper/store (`logo`, `storeType`, `brandId`, `deliveryPrice`). 
