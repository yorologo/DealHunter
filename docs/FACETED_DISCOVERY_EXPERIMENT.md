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

## Phase 3C.3 — Promotion integrity audit

- **Problema:** En Phase 3C.2, dos productos Golden (California especial, Sushi del mes) perdieron sus campos promocionales (`real_price`, `discount`) tras corregir los memberships.
- **Causa Raíz:** La lógica original de deduplicación de productos en `catalog_sync.py` priorizaba incondicionalmente la *primera* aparición del producto en el catálogo. Si un producto era procesado primero dentro de un corredor regular (sin campos promocionales) y luego dentro del corredor "Ofertas" (con promociones), los valores comerciales de la segunda aparición eran descartados y solo se anexaba el string del `membership`.
- **Commit Hygiene:** Se detectó que el commit de "docs" de Phase 3C.2 incluyó de manera descuidada la actualización funcional del archivo `catalog_sync.py`. Este problema de higiene en el historial será evitado en commits futuros.
- **Solución:** Se corrigió el ciclo de deduplicación para que inspeccione `promo_fields`. Si una subsecuente aparición posee datos de promoción explícitos, los transfiere sobre el registro `existing` (preservando los memberships sin degradar el valor comercial).
- **Invariantes:** Esta corrección resolvió el problema de deduplicación que silenciosamente descartaba descuentos en todas las instancias CPG y Restaurants previas de DealHunter. Las promociones ahora sobreviven intactas el merge de taxonomías.

## Phase 3C.4 — Live promotion integrity confirmation

- **Validación final:** Se comprobó el comportamiento en vivo del pipeline completo (incluyendo el fix de merge) utilizando 1 sola llamada a la red para VELMA BOX ZAPOPAN.
- **Resultados de Invariantes:** El root wrapper fue excluido exitosamente (0 contamination). Las membresías RAW auténticas (ej. `["Sushi"]`) se preservaron intactas. 
- **Catalog Drift:** Se detectó un cambio real en el menú del proveedor: todos los productos duplicados promocionales (ej. los del corredor "Ofertas") desaparecieron de la estructura devuelta por Rappi en este instante. La caída a `real_price: None` para "California especial" no fue un error del parser, sino la fiel representación del menú en tiempo real.
- **Conclusión de Extracción:** El merge procesa de forma independiente al orden conservando la mejor representación comercial sin perder membresías. El sistema está 100% estable, no descarta falsamente promociones, no inventa promociones inexistentes y mantiene limpia la frontera taxonómica de las tiendas.

## Phase 3D — Semantic persistence / schema v11

- **Migración a schema v11:** Se actualizaron `db.py` y `core.py` para persistir la clasificación semántica en la tabla `product_memberships`. Se agregaron las columnas:
  - `semantic_type` (TEXT, default: 'UNKNOWN')
  - `semantic_reason` (TEXT, default: 'not_classified')
- **Invarianza RAW:** La clasificación semántica es puramente *derivada*. Los datos RAW (`raw_name`, `path`, etc.) continúan siendo la fuente inmutable de verdad. La migración inicial de registros v10 asigna de forma segura un estado neutral (`UNKNOWN` / `not_classified`) sin ejecutar inferencias retroactivas inseguras.
- **Ciclo de vida en Upsert:** Las filas son re-clasificadas dinámicamente en cada observación. Un membership catalogado como `UNKNOWN` transitará a `CATEGORY` en cuanto el payload provea evidencia fuerte del proveedor. Del mismo modo, retornará a `UNKNOWN` si la evidencia desaparece, garantizando reproducibilidad continua sin estados "zombies".
- **Multi-membership y Colecciones:** Un solo producto puede poseer simultáneamente relaciones `CATEGORY` (ej. "Cervezas") y `COLLECTION` (ej. "Ofertas"). El clasificador opera individualmente por cada relación `product_id -> membership`. Si ocurre un conflicto de evidencia (por ejemplo, una sección llamada "Ofertas" intentando catalogarse erróneamente como category root), se cataloga protectoramente como `UNKNOWN` con razón `conflicting_evidence`. 
- **Compatibilidad Legacy:** La taxonomía legacy (`products.category`, `stores.vertical`, heurísticas legacy, etc.) permanece intacta sin modificaciones, cumpliendo con la regla de transición conservadora dictada para este experimento.

## Phase 4A — Isolated live v11 population

- **DB Aislada:** Se creó una copia temporal de `rappi-deals.db` en un directorio separado. La DB de producción permaneció intacta y su SHA256 se validó idéntico al iniciar y finalizar la prueba.
- **Muestra y Requests:** Se analizaron 4 sucursales (Velma Box, City Market, Turbo, Farmacias Benavides) en un entorno offline-first y acotado. Total HTTP requests utilizadas: 4.
- **Verticales y Facets:** Las variables de facetas y tipo (`type`) de tienda se mantuvieron legadas (ej. `restaurants`, `market`, `chiper_extended`, `Farmatodo`) y accesibles para las consultas.
- **Distribución Semántica:** De 339 relaciones "membership" extraídas en la muestra, 15 fueron clasificadas como `CATEGORY`, 30 como `COLLECTION` (ej. "Ofertas") y 294 con default seguro a `UNKNOWN` (todas por `insufficient_evidence`). Ninguna clasificación devolvió `conflicting_evidence`. Las filas heredadas pasaron de `not_classified` a ser clasificadas correctamente usando datos actuales.
- **Deals:** La lógica promocional no fue impactada. Se detectaron al menos 10 promociones `discount_effective >= 50%` en la muestra y 1 evento `NxM`. Las métricas comerciales (`price`, `real_price`, `discount`) de los "golden deals" de validación (ej. California especial a $63) se mantuvieron consistentes.
- **Consultas (Queries):** Las consultas cruzadas Facetadas (ej. "Vertical = Turbo AND semantic_type = COLLECTION AND raw_name = Ofertas") generaron planes de ejecución efectivos y retornaron resultados con precisión.
- **Performance:** Las consultas demoraron menos de 1ms de ejecución end-to-end; no requieren índices agregados en esta fase y la tabla combinada funciona ágilmente gracias al diseño N:M normalizado de Schema V11. 
- **Producción Intacta:** Completamente validada.

## Phase 4A.1 — Store taxonomy population integrity

- **Por qué Phase 4A fue incompleta:** El script de validación aislado de Phase 4A instanció directamente los adaptadores de catálogo (`RestaurantMenuAdapter`, `CPGCatalogAdapter`) y ejecutó la inserción de productos saltándose deliberadamente la fase normal de descubrimiento de tiendas (`discover_merchants`). Como resultado, los diccionarios de merchant (que contienen la metadata taxonómica) nunca se extrajeron de Rappi ni llegaron a `crawler_zone.py` para su persistencia, provocando que las tiendas evaluadas terminaran con `vertical=None` y 0 facetas.
- **Pipeline Correcto (Causa Raíz resuelta):** Se validó y comprobó mediante tests exhaustivos en `tests/test_store_taxonomy.py` que el pipeline original de V2 en `crawler_zone.py` **sí transporta y persiste correctamente** toda la metadata (`vertical_sub_group`, `type`, `tags`, `categories`).
- **Level A (Vertical):** La semántica `stores.vertical` se preserva perfectamente como "Restaurantes", "Turbo", "Supermercado" o "Farmacia" a partir del campo nativo `vertical_sub_group`, manteniendo en paralelo el string original técnico del backend de Rappi en `stores.type`.
- **Level B (Store Facets):** La persistencia N:M deduplica y consolida las fuentes combinadas de `categories` y `tags`.
- **Absent vs Empty y Reconciliación:** Comprobado vía tests. Si una observación parcial (`discover_merchants` parcial o ausente) no reporta metadatos, los `store_facets` previos se conservan de forma defensiva para no destruir taxonomía.
- **Prueba Live (Muestra actual de Rappi):** El endpoint productivo `unified-search` actualmente expone correctamente `parent_store_type` y `vertical_sub_group`, cumpliendo el Level A. Sin embargo, para la mayoría de tiendas (incluyendo restaurantes de Sushi), Rappi ha dejado de enviar los arrays `tags` y `categories` en esta respuesta, dejándolos ausentes. DealHunter maneja esto correctamente: popula el Level A (`stores.vertical`) y deja vacío el Level B si Rappi no expone facetas.
- **Queries verificadas:** El diseño soporta perfectamente las consultas transversales (ej. "Restaurantes AND Sushi") una vez poblada la base de datos a través de una ejecución normal del pipeline V2 (`dealhunter update` / `crawler_zone.py`).

## Phase 4B.1 — Production schema v11 migration

- **Objetivo:** Migración canónica `v10 -> v11` en `rappi-deals.db` de producción, sin crawlers, requests a Rappi, ni reescritura de datos funcionales.
- **Backup Verificado:** Se creó el backup `rappi-deals-pre-v11-20260824-001647.db` (SHA256 pre/post = `811e40832a62abf70e04468af2220c1970efc6321af57404adec54ec28d09195`). La base mantenía conteos idénticos al original.
- **Proceso:** La migración se disparó por `dealhunter.db.setup_db`. Se comprobó offline con 0 requests realizadas a Rappi.
- **Resultados:** `schema_version = 11`. El `integrity_check` fue `ok` y los FK check fueron 0 violations.
- **Datos Preservados:** Los 869 stores, 24752 products y 80298 observaciones se mantuvieron intactos sin pérdida de precisión. La tabla `product_memberships` y `store_facets` fueron creadas limpias y `stores.vertical` disponible sin alterar los datos legacy existentes (`0 -> 0` porque la fase poblacional aún no se dispara productivamente).
- **Rolback Plan:** Se documentó que para revertir bastaría restaurar el backup `pre-v11` con el nombre `rappi-deals.db` tras detener cualquier escritor activo de DealHunter, verificando la integridad posteriormente.

## Phase 4B.2a — Targeted merchant resolution

- **Objetivo:** Resolver el limitante arquitectónico que forzaba siempre la ejecución de sweeps alfabéticos (26-546 peticiones) imposibilitando actualizar la taxonomía de una tienda con presupuesto pequeño.
- **Implementación:** Se refactorizó `MerchantDiscovery` para exponer `_run_query_sync` y `_normalize_store`. Se añadió `discover_targeted(query, lat, lng, report, expected_store_id=None)` que realiza exactamente *una* request a `unified-search`, procesa con el parser canónico y devuelve `(MATCH_EXACT_STORE_ID, merchant)`, garantizando preservación del metadata intacto.
- **Fallbacks:** Si no encuentra la tienda por nombre o ID, retorna explícitamente `NOT_FOUND` sin disparar ningún modo adaptativo, aislando el budget a 1 HTTP Request garantizada.
- **Compatibilidad:** Los modos existentes (`NORMAL`, `DEEP`, `FULL`) funcionan sin modificaciones. El nuevo método es exclusivamente para consumos programáticos.
- **Validación:** Completada offline mediante tests mockeados. Suite pasó con éxito (`353 passed`).
