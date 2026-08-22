# Doctor

El módulo `doctor` de DealHunter diagnostica la salud del sistema.

## Doctor Local
Se invoca vía CLI (`bin/rappi-ofertas doctor`) o vía Web en la interfaz de Administración (`/admin/doctor`).
Revisa:
- Conectividad a la Base de Datos.
- Disponibilidad del entorno de ejecución.
- Variables de entorno (`RAPPI_BEARER_TOKEN`).

## Doctor de Red (Network Doctor)
Es una acción explícita (opt-in) que verifica la conectividad hacia los servicios del proveedor.
- Desde la Web, requiere presionar un botón que dispara un `POST` con protección CSRF.
- Respeta límites de Cloudflare (HTTP 429) y Timeout.
- No incluye reintentos infinitos ni evasión de rate limits.


- **Background Runtime (Termux)**: Verifica si Termux está activo y si `termux-wake-lock` está habilitado. Si está ACTIVO, advierte que el lock pertenece globalmente a Termux y no será liberado automáticamente.