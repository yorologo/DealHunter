# Security & Privacy

DealHunter mantiene un modelo local-first y aplica fallos cerrados en los límites sensibles.

- **Host seguro**: la web se vincula por defecto a `127.0.0.1`.
- **GET sin mutación**: las rutas de navegación no deben modificar estado ni ejecutar adquisición remota.
- **POST + CSRF**: toda acción mutable requiere POST y token CSRF válido.
- **Jinja autoescape**: las plantillas conservan escape HTML por defecto.
- **SecretStore**: las sesiones persistentes usan exclusivamente cifrado autenticado Fernet provisto por `cryptography`. `.session_salt` y `session.enc` se escriben como archivo temporal privado → `fsync` → `0600` → reemplazo atómico. Un fallo parcial conserva el secreto anterior y se reporta explícitamente; NOT_CONFIGURED, CORRUPTED y STORAGE_ERROR no se colapsan entre sí.
- **Sin fallback débil**: no se permite plaintext, base64, firma sin cifrado ni criptografía casera como sustituto del SecretStore.
- **Flask session key**: `SECRET_KEY` de entorno tiene prioridad. Sin override, DealHunter crea una clave aleatoria persistente en `~/.config/dealhunter/flask_secret.key` (o `XDG_CONFIG_HOME`) y fuerza permisos `0600`; no existe fallback `dev`.
- **Aislamiento**: tokens de sesión no entran en SQLite, `config.toml`, templates, logs ni backups generales.
- **Filesystem**: `.db`, `.bak` e historial personal no se sirven desde estáticos públicos.
- **Backups SQLite**: un backup sólo se acepta después de reabrirlo, ejecutar `PRAGMA integrity_check` y comprobar que su versión de schema coincide con la fuente. Un resultado inválido se elimina y se reporta como error.
- **Sin ejecución arbitraria**: la web no expone SQL arbitrario ni construcción de shell desde input del usuario.
- **Redirects locales**: destinos controlados por formularios/Referer sólo pueden volver a rutas internas o same-origin; URLs externas y `//host` nunca son destinos de redirección.

## Termux y `cryptography`

En Termux usa preferentemente el paquete nativo cuando esté disponible:

```bash
pkg install python-cryptography
```

Si trabajas dentro de un venv en Termux, usa `python -m venv --system-site-packages .venv` para que el entorno vea ese backend nativo. DealHunter marca la dependencia pip de `cryptography` como no aplicable en `sys_platform == "android"` para evitar sustituirla accidentalmente por un wheel incompatible.

En el entorno validado con Python 3.14.6, `python-cryptography 50.0.1` carga Fernet sin `LD_PRELOAD`. No configures `LD_PRELOAD` global como requisito de DealHunter. Si `cryptography` no carga, corrige el runtime/paquete; no debilites SecretStore.

## Privacy Philosophy

DealHunter extrae catálogos comerciales y evita persistir datos personales que no sean necesarios para la función local. En particular, no debe almacenar deliberadamente cookies completas, datos de pago, direcciones personales ni historiales ajenos.
