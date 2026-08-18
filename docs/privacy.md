# Privacidad y Manejo de Datos

DealHunter es un motor orientado al respeto riguroso de la información de usuario final.

## ¿Qué datos guarda?
* **Localmente (SQLite):** Guarda los IDs de las tiendas, los productos descubiertos, el historial de precios observados y las horas en que corriste los escaneos.
* Todas las bases de datos residen en la carpeta donde clonaste el repositorio bajo la extensión `*.db`.

## ¿Qué datos NO guarda?
* No guarda credenciales, tokens, contraseñas ni cookies.
* No guarda datos de medios de pago.
* No guarda direcciones de casa. Se requiere explícitamente enviar coordenadas decimales (`lat`, `lng`) al iniciar el CLI, pero éstas no se ligan a cuentas residenciales ni se comparten en red.

## Arquitectura Offline
Toda la analítica pesada (`rappi-historico`), el cómputo de la mediana de 30 días, y el dictamen de las ofertas, ocurren enteramente **offline** ejecutándose de tu base de datos local a tu pantalla de terminal, sin emitir telemetría externa a terceros.
