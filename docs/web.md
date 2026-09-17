# Web UI

DealHunter usa una capa Web deliberadamente delgada:

```text
Browser → Flask/Jinja/HTMX → query/domain services → SQLite
```

- Flask + Jinja2 para SSR.
- HTMX para interacciones parciales.
- Bootstrap 5 y Chart.js vendorizados; no hay CDN en runtime.
- SQLite y servicios de dominio siguen siendo la autoridad; la Web no reimplementa Price Intelligence, matching, alertas ni configuración efectiva.

## Navegación

La interfaz agrupa las funciones en cuatro áreas:

- **Comprar**: oportunidades, supermercados, Turbo, restaurantes y categorías.
- **Investigar**: productos, tiendas, detalle, histórico, búsqueda y comparación.
- **Seguir**: Watchlist y Alertas de sólo lectura sobre los motores existentes.
- **Administrar**: Cuentas / Proveedores, runs/eventos, Doctor, DB/backup, Settings y Catalog Sync.

El mapa exacto de rutas es código (`src/dealhunter/web/routes.py` y `admin.py`), no una tabla duplicada que deba sincronizarse manualmente con cada cambio.

## Límites de seguridad

- La Web escucha por defecto sólo en `127.0.0.1`.
- GET de navegación no debe ejecutar adquisición remota ni mutar estado.
- Acciones mutables usan POST + CSRF.
- Secrets nunca se renderizan; la UI sólo muestra estado/configuración segura.
- Cuentas / Proveedores y Doctor separan diagnóstico local de validación de red; cualquier comprobación remota requiere una acción POST explícita.
- Backup/integrity usan funciones internas; no existe SQL arbitrario en la UI.
- `/api/open-rappi` construye únicamente deep links soportados desde IDs/tipos resueltos en SQLite y falla cerrado si Shizuku/Intent/tipo no son válidos.

## Cuentas / Proveedores

`/admin/account` presenta Rappi y Uber Eats en una sola superficie, pero conserva sus mecanismos aislados:

- **Rappi** → `SessionService` / SecretStore / `get_account_status()`. En Android/Termux, **Configurar desde este teléfono** reutiliza el mismo bookmarklet que `dealhunter auth rappi --mobile`: un POST explícito crea un nonce efímero, el bookmarklet vuelve a un endpoint loopback mediante `#fragment`, la página local elimina inmediatamente el fragmento y hace un POST same-origin + CSRF para persistir y validar. El wizard PC/navegador existente sigue disponible.
- **Uber Eats** → profile Chromium / runtime CDP / autoridad `providers/uber_eats/status.py`.

El GET es diagnóstico local: no genera nonce, no navega a Uber y no valida Rappi por red. Los botones **Comprobar sesión** ejecutan únicamente la validación explícita del provider correspondiente. Catalog Sync consume la sesión Rappi existente y remite a Account para gestionarla; no mantiene otra UX de autenticación. La existencia del profile Uber se muestra como `UNVERIFIED`, nunca como prueba de sesión válida. Si Uber necesita login o renovación, la Web indica `dealhunter uber setup`; no ejecuta Carbonyl ni expone controles Start/Stop Chromium.

## Configuración

`/admin/settings` presenta primero tareas humanas y conserva la autoridad existente de `config.py`: ubicación, providers, membresías y modo de exploración. Los detalles técnicos y la precedencia viven en **Ajustes avanzados** dentro de la misma página.

La ubicación persistente sigue siendo únicamente `lat` + `lng` en `config.toml`. **Usar ubicación de este dispositivo** llama a `navigator.geolocation` sólo después de un click explícito; muestra latitud, longitud y precisión aproximada para confirmación, pero sólo envía/persiste `lat` y `lng`. Si la API del navegador no está disponible, el mismo endpoint acepta entrada manual de ambas coordenadas. No hay GeoIP, geocoder externo ni dirección/código postal.

El runtime global es editable desde Web. Un profile seleccionado se muestra para diagnóstico pero es **solo lectura**; su edición avanzada permanece en CLI/configuración. Restaurar un ajuste avanzado elimina el override global para que la precedencia vuelva a resolver el default/profile correspondiente.

## Runs y progreso del crawler

**Iniciar crawler Rappi** representa el provider real del flujo Web actual. `GET /admin/runs` comprueba localmente si la ubicación efectiva es válida: si falta, muestra un modal que enlaza a Settings y no envía el POST. Guardar ubicación desde ese flujo vuelve a Runs, pero nunca inicia adquisición automáticamente. El backend de `POST /admin/runs/start` vuelve a validar `lat/lng`, reserva exactamente un `run_id`, lanza el proceso y navega a su detalle.

Mientras un run está `RUNNING`, el progreso pertenece al `run_id` y se persiste en `runs.run_metadata`. El detalle reconstruye desde SQLite un modal bloqueante incluso después de recargar la página y consulta únicamente un endpoint local ligero cada 3 segundos. Zone Inventory muestra porcentaje sólo después de conocer el número real de merchants; Search Discovery permanece indeterminado cuando su conjunto de consultas puede crecer dinámicamente. El ETA se deriva de unidades realmente completadas y no avanza por tiempo artificial.

## Catalog Sync

Con sesión Rappi válida se usa Zone Inventory. Sin sesión o con sesión no válida, Search Discovery mantiene cobertura limitada sin reconciliación destructiva. Un fallo parcial no convierte ausencias no observadas en bajas definitivas.

El scheduler se administra desde la UI o `dealhunter scheduler`; la política operativa canónica está en `operations.md`.
