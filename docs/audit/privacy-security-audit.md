# Auditoría de Seguridad y Privacidad

Esta auditoría garantiza que el código que se va a publicar no contenga PII (Información Personal Identificable), secretos, ni vulnere los servidores objetivo mediante credenciales filtradas.

## Hallazgos

### 1. Tokens y Credenciales de API
**Estado:** `SAFE`
**Detalle:** El proyecto evolucionó (v2) para utilizar el endpoint público de búsqueda unificada de Rappi (`/api/pns-global-search-api/v1/unified-search`), el cual no requiere cabeceras `Authorization`, `x-rappi-token`, ni `Cookies`. No hay credenciales hardcodeadas en ningún script.

### 2. Identificadores de Dispositivo y Usuario
**Estado:** `SAFE`
**Detalle:** Se han omitido y purgado cabeceras rastreables como `device_id`, `android_id`, y `user_id`. El script utiliza un `User-Agent` genérico de navegador y no falsifica huellas digitales invasivas.

### 3. Coordenadas y Ubicación
**Estado:** `SANITIZE` -> `SAFE` (Mitigado)
**Detalle:** El script original tenía quemadas las coordenadas por defecto en `main()` (CDMX). Aunque no es una ubicación personal sensible (es el centro de la ciudad), se migraron a parámetros CLI `--lat` y `--lng` para evitar exponer zonas de prueba locales.

### 4. Bases de Datos y Logs (SQLite)
**Estado:** `IGNORE_FROM_GIT`
**Detalle:** El archivo `rappi-deals.db` contiene la recolección del usuario. Puede incluir qué zonas rastreó y cuándo. Se ha añadido al `.gitignore` explícitamente, junto con sus archivos transaccionales (`-shm`, `-wal`) y los respaldos (`pre-history.db`).

### 5. Dumps y Archivos de Investigación (Blutter / Shizuku)
**Estado:** `IGNORE_FROM_GIT`
**Detalle:** Los directorios `~/rappi-analysis/` y los outputs como `audit_deals.json`, `coverage-audit.json` o volcados crudos están excluidos en `.gitignore` para no filtrar binarios o respuestas JSON reales.

## Conclusión
`SAFE FOR GITHUB`. El repositorio local ha sido sanitizado.
