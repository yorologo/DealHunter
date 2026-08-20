# Security & Privacy

DealHunter asume y respeta los límites del modelo local garantizando un marco robusto contra vulnerabilidades habituales de la web.

- **Host Seguro**: Default bind a `127.0.0.1`.
- **Read-Only Nav**: Rutas web GET no mutan base de datos ni ejecutan rutinas remotas no deseadas.
- **Explicit POSTs & CSRF**: Toda acción mutable requiere POST validado contra un token CSRF (generado dinámicamente) de forma imperativa.
- **Templating**: Autoescape activo de Jinja2 (`XSS` prevention).
- **Secrets Isolation**: Credenciales viajan puramente vía environment, nunca son cacheadas en SQLite, renderizadas en logs o en atributos ocultos HTML.
- **File System**: Archivos `.db`, `.bak` e historial personal no son nunca servidos desde directorios estáticos públicos. No se expone *path traversal* (ej. el backup se autoasigna su nombre).
- **No Arbitrary Execution**: Se deniega rotundamente ejecución SQL por la web o shell injection.

## Privacy Philosophy
DealHunter solo extrae catálogos comerciales. NO persigue persistir ni rastrear:
- Cookies.
- Pagos.
- Direcciones.
- Historiales ajenos.
