# Historia Técnica del Descubrimiento

La ruta de creación de *Rappi Deal Hunter* no partió de un ataque frontal, sino de un análisis progresivo del cliente nativo para recuperar información estructurada (no depender de OCR). Las transiciones más vitales fueron:

### 1. Proof of Concept: Termux, Shizuku, y UIAutomator
**Hipótesis:** ¿Podemos dumpear el layout XML en pantalla y recuperar ofertas directamente leyendo la pantalla?
**Resultado:** Técnicamente posible; construimos un minero en base a `adb shell uiautomator dump`. 
**Decisión:** Abandonado a los días. Excesivamente lento, fallaba en renders off-screen y consumía muchísima memoria.

### 2. Reconocimiento de Red y Static Analysis (APK + Blutter)
**Hipótesis:** Si el app recibe los datos de ofertas estructurados, podíamos interceptar red o auditar el paquete.
**Prueba:** Se extrajo el APK (Split-Config) a Termux, localizando la base y extrayendo los binarios Flutter (Dart 3.9). Usamos `Blutter` en el CLI para desensamblar `libapp.so`.
**Resultado:** Se rastrearon constantes de red y la arquitectura Server-Driven UI (SDUI). Se aislaron los nombres de dominio de dev (`microservices.dev.rappi.com`) y los productivos (`services.mxgrability.rappi.com`).

### 3. Migración y Probing del API Universal
**Hipótesis:** Una vez detectados los dominios, ¿podemos saltar por completo la capa de SDUI (que viene cruda con componentes gráficos y no raw data) para extraer catálogo neto?
**Prueba:** Se desarrolló y ejecutó un batery test (`api-prober`) comprobando `/api/cpgs-orders/`, `/api/ms/shopping-cart/v1/` y catálogos de tiendas puntuales. Todos respondían con Rate Limiting extremo (Cloudflare 1015 IP Bans) a la primera o segunda consulta.
**Resultado:** Localizamos el sub-microservicio de "Unified Search" (`/api/pns-global-search-api/v1/unified-search`). Este se comportó infinitamente más escalable, resiliente a rate limit en modo secuencial (`time.sleep(3)`), sin `Authorization` token requerido. 

### 4. Modelo de Minería por Verticales e Histórico (v2)
**Evolución Actual:** Teniendo la puerta descubierta, la simple búsqueda de keywords fue orquestada en colas adaptativas que se bifurcan cuando detectan productos de nicho. Finalmente, superamos la manipulación "Visual" de ofertas trasladando el "original_price" sugerido de la aplicación, al histórico real `median_30d` almacenado en disco (`rappi-historico`).
