# Política de Seguridad

DealHunter es local-first, pero sí puede manejar **sesiones autorizadas de proveedor** cuando el usuario decide configurarlas. No implementa pagos ni escribe compras/cambios de cuenta, pero un token de sesión sigue siendo un secreto sensible.

## Sesiones y credenciales

- `RAPPI_BEARER_TOKEN` puede usarse de forma efímera desde el entorno.
- La Web/CLI también permiten persistencia **opt-in** mediante `SecretStore`.
- Las sesiones persistentes se cifran localmente con Fernet (`cryptography`) y archivos privados; no existe fallback a plaintext, base64 o firma sin cifrado.
- Los tokens no deben entrar en SQLite, `config.toml`, templates, logs, backups generales ni commits.
- La importación/configuración de una sesión requiere una acción explícita del usuario; DealHunter no intenta extraer credenciales automáticamente de otras apps.

La política técnica detallada, incluido fail-closed de SecretStore, CSRF, redirects y Termux `cryptography`, está en [`docs/security.md`](docs/security.md).

## Reporte de vulnerabilidades

Si descubres una vulnerabilidad o una posible fuga de credenciales/PII, evita publicar secretos o datos personales en un issue público. Describe el problema con datos sintéticos o redactados y utiliza un canal privado del repositorio/propietario cuando sea posible. No incluyas tokens reales, cookies, direcciones, métodos de pago ni dumps de sesiones.
