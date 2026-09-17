# Account Diagnostics

DealHunter está diseñado primariamente como una herramienta read-only que rastrea catálogos públicos. Sin embargo, para ciertos proveedores o depuración avanzada, se puede proveer un token de sesión opcional de manera local.

## Comando
```bash
rappi-ofertas account status
```

El diagnóstico valida la cuenta usando la sesión efectiva resuelta por `SessionService`: primero `RAPPI_BEARER_TOKEN` (efímero), luego una sesión temporal y finalmente SecretStore persistente si el usuario la configuró explícitamente. Retorna sólo contexto seguro (por ejemplo, estado, mercado y membresía).

## ¿Qué consulta?
Exclusivamente el estado actual de la sesión.
La información que se parsea incluye:
* Estado de la sesión (`VALID`, `UNAVAILABLE`)
* Región / Mercado
* Indicador de Membresía (Prime)
* Contexto de beneficios disponibles

## ¿Qué NO consulta?
El sistema **no implementa** ni implementará operaciones de escritura en la cuenta (compras, cambios de dirección, alteración de listas). No consulta métodos de pago ni historial exhaustivo de compras.

## Limitaciones y Privacidad (NOT_SAFE_TO_IMPLEMENT)
Para extraer el token de sesión dinámicamente de la app móvil en tu dispositivo, haría falta acceso `root` o inyección de código. Dado que nuestro principio fundacional dicta cero invasividad:
* La extracción automática de credenciales está marcada como **`NOT_SAFE_TO_IMPLEMENT`**.
* No se provee ningún bypass de autenticación.
* DealHunter no extrae automáticamente credenciales desde la app. El usuario debe autorizar/proveer la sesión mediante los flujos soportados.
* La persistencia es opcional: `RAPPI_BEARER_TOKEN` permanece efímero; el modo persistente usa SecretStore cifrado y puede eliminarse desde los controles de sesión.

> Las sesiones persistentes son opt-in y permanecen sólo en el dispositivo local, cifradas por SecretStore; no se guardan en SQLite ni en `config.toml`.

## Sanitización y Seguridad
Si el sistema utiliza tu token para consultar el estatus de la cuenta, respeta la siguiente regla dura:

`consultar -> sanitizar -> mostrar -> descartar`

NUNCA se imprimen ni guardan en disco (ni en SQLite, logs o `config.toml`) datos sensibles devueltos por el API, incluyendo:
* Nombre real, email y teléfono
* Direcciones de entrega completas
* Identificadores de dispositivos
* Métodos de pago

Si la sesión expira o es incorrecta, se lanzará un error estructurado `ACCOUNT_SESSION_UNAVAILABLE`.
