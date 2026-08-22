# Diagnóstico de Mecanismos de Autenticación y Catálogos

## 1. Mecanismos Actuales (Status Quo)
- **Descubrimiento y Catálogos:** DealHunter utiliza `https://services.mxgrability.rappi.com/api/pns-global-search-api/v1/unified-search`
  - **Autenticación:** Completamente anónima. No requiere `Authorization`, cookies, ni tokens de sesión.
  - **Limitaciones:** Paginación estricta (aprox 20-30 productos por tienda). Ignora los filtros por `store_id`. No es un endpoint de catálogo, sino un buscador global. Imposible alcanzar el 100% de cobertura.
- **Diagnóstico de Cuenta:** Usa `https://services.mxgrability.rappi.com/api/ms/users/profile`. 
  - **Autenticación:** Requiere `Authorization: Bearer <TOKEN>`.
  - **Estado:** Actualmente el token se pasa de forma efímera vía variable de entorno `RAPPI_BEARER_TOKEN`.
- **Endpoints de Catálogo Nativos Probados:**
  - `api/cpgs-integration/v1/store-detail/...` -> Responde `403 Forbidden` sin autenticación.
  - `api/ms/restaurants-catalog/v1/catalog/store/...` -> Responde `403 Forbidden`.

## 2. Investigación de Tráfico Android
**Resultado:** `AUTH_CAPTURE_BLOCKED_BY_APP_SECURITY`
- Al intentar utilizar herramientas locales (Shizuku) para inspeccionar el tráfico o extraer el token desde `/data/data/com.grability.rappi/`, el servicio falla por timeout/bloqueo de permisos en este entorno (Termux sin root total habilitado o con batería optimizada).
- Inspeccionar el tráfico HTTPS vía proxy local requeriría vulnerar el *certificate pinning* de la app, lo cual viola las directivas arquitectónicas.

## 3. Estrategia: Reutilización de Sesión Web
Rappi Web (Next.js) utiliza autenticación mediante tokens opacos inyectados en las peticiones AJAX. 
- **Flujo diseñado (`dealhunter auth rappi`):**
  1. DealHunter inicia un servidor local efímero.
  2. El usuario navega a `www.rappi.com.mx` e inicia sesión legalmente (OTP/reCAPTCHA manejado por Rappi).
  3. El usuario utiliza un *Bookmarklet* proporcionado por DealHunter para interceptar las peticiones AJAX nativas (V7 Omni-Interceptor) para extraer el token de manera opaca y enviarlo de vuelta a `localhost:5000/auth/callback`.
  4. DealHunter recibe el `AccessContext`, apaga el servidor y guarda el material de forma segura en `~/.config/dealhunter/session.enc` (0600), fuera de logs y variables expuestas.

## 4. Endpoints por Descubrir
Debido a la directiva de "No suponer endpoints", los adaptadores `CPGCatalogAdapter` y `RestaurantMenuAdapter` se implementarán utilizando un esquema de fallback hasta que, usando el nuevo token inyectado, podamos probar (Probe) y observar las rutas exactas de catálogo.

## Mobile browser authentication

### Arquitectura y Límites de Seguridad
Para sortear la imposibilidad de usar DevTools (F12) en navegadores móviles (Android/Termux), se ha implementado el modo `--mobile`. El flujo funciona generando dinámicamente un bookmarklet en la terminal. El usuario debe crear un marcador con este código y ejecutarlo explícitamente estando en `www.rappi.com.mx`.

1. **Servidor Efímero Loopback**: El servidor `LocalAuthImporter` se inicializa escuchando exclusivamente en `127.0.0.1` (loopback), en un puerto efímero aleatorio (`port=0`). Nunca escucha en interfaces públicas (`0.0.0.0`), garantizando que ninguna app o dispositivo en la LAN/Wi-Fi pueda conectarse a él.
2. **CORS y el Fragment Trick**: Para evadir políticas de CORS que bloquean peticiones HTTP `fetch()` desde `https://www.rappi.com.mx` hacia `http://127.0.0.1:<puerto>`, el bookmarklet hace una navegación pura inyectando el payload JSON base64-encodificado en el **fragmento** (`#...`). El navegador no envía los fragmentos en la petición HTTP al servidor, evadiendo así inspección de tráfico local.
3. **Página Importadora**: DealHunter devuelve un HTML mínimo (`do_GET`) que lee el fragmento, lo elimina inmediatamente de la barra de direcciones (`history.replaceState`), y despacha un POST `fetch()` *same-origin* hacia `/commit`.
4. **Nonce Criptográfico**: El servidor de importación requiere un `nonce` aleatorio de 16-bytes (32 hex chars) que se genera en memoria por ejecución. Se acepta un único payload correcto y el servidor se auto-destruye y se apaga inmediatamente tras la importación.
5. **Por qué no se intercepta TLS o se usa Shizuku**: Las medidas defensivas de Rappi incluyen **Certificate Pinning**, por lo que montar un servidor MITM local está destinado a fallar o ser bloqueado. *Shizuku* falla en nuestro ambiente (Termux) por timeout del servicio o falta de privilegios del sistema para el directorio aislado. La exportación voluntaria vía bookmarklet esquiva toda ofuscación de la app nativa y utiliza la sesión autorizada de la web que el usuario controla.
6. **No uso de Query Strings**: El payload nunca se pasa vía parámetros `?token=...` en la URL de navegación local, pues esto dejaría rastros en historiales y access logs. Se confina al URI fragment y al POST body.
