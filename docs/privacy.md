# Privacidad y Manejo de Datos

DealHunter es un motor orientado al respeto riguroso de la información de usuario final.

## ¿Qué datos guarda?
* **Localmente (SQLite):** Guarda los IDs de las tiendas, los productos descubiertos, el historial de precios observados y la procedencia `timestamp/lat/lng` de cada run.
* Todas las bases de datos residen en la carpeta donde clonaste el repositorio bajo la extensión `*.db`.

## ¿Qué datos NO guarda?
* No guarda credenciales, tokens, contraseñas ni cookies.
* No guarda datos de medios de pago.
* No guarda el texto de direcciones de casa. Las coordenadas decimales (`lat`, `lng`) se conservan localmente en `config.toml` y a nivel de run para hacer auditable la zona de captura; no se añaden a Git ni se muestran completas en reportes.
* La jerarquía UI, capturas u OCR usados durante un diagnóstico de cuenta/zona o una validación manual de navegación son temporales, no capturan precios y deben eliminarse al terminar.

## Arquitectura Offline
Toda la analítica pesada (`rappi-historico`), el cómputo de la mediana de 30 días, y el dictamen de las ofertas, ocurren enteramente **offline** ejecutándose de tu base de datos local a tu pantalla de terminal, sin emitir telemetría externa a terceros.
