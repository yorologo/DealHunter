# DealHunter

DealHunter es un motor **local-first** de inteligencia de precios para Rappi y Uber Eats. Guarda el histórico en SQLite, compara precios reales y expone una Web local para explorar oportunidades sin depender de un backend de DealHunter.

Última release pública: **v3.3.1**. La rama `develop` contiene trabajo posterior aún no publicado como una nueva versión.

## Instalación rápida — Android / Termux

Requisito previo: Termux con acceso a Internet y `git` para clonar el repositorio.

```bash
pkg install git
git clone https://github.com/yorologo/DealHunter.git
cd DealHunter
git checkout main
./install.sh
```

El instalador:

- instala sólo dependencias Termux faltantes; no ejecuta `pkg upgrade`;
- usa `python-cryptography` nativo en Android;
- instala DealHunter desde `pyproject.toml` con `pip install .`;
- verifica Python, `cryptography` y el comando `dealhunter`;
- puede ejecutarse de nuevo de forma segura después de una actualización.

Inicia la Web:

```bash
dealhunter web
```

Abre `http://127.0.0.1:8765`. Antes del primer sync configura **lat/lng** en **Admin → Settings**. Ésa es la única configuración obligatoria para adquirir datos de una zona.

Para quien prefiera CLI:

```bash
dealhunter config set lat TU_LATITUD
dealhunter config set lng TU_LONGITUD
dealhunter doctor
dealhunter sync --provider rappi
```

La sesión autenticada de Rappi, Uber Eats, membresías y scheduler son opcionales; DealHunter no necesita credenciales para arrancar la Web.

## Uso diario

```bash
# Web local
dealhunter web

# Diagnóstico local
dealhunter doctor

# Sincronización manual
dealhunter sync --provider rappi
dealhunter sync --provider uber_eats

# Estado/backup/integridad de SQLite
dealhunter db status
dealhunter db backup
dealhunter db integrity

# Scheduler administrado por DealHunter
dealhunter scheduler enable
dealhunter scheduler status
```

El scheduler exige `lat/lng` válidos y usa una sola política administrada: Rappi a `07:00/10:00/13:00/19:00` y Uber Eats a `07:30/10:30/13:30/19:30`, con `flock` para evitar solapamientos. En Termux debe existir un `crond` activo.

## Actualizar una instalación de release

Con un checkout limpio en `main`:

```bash
./update.sh
```

`update.sh` crea un backup SQLite cuando DealHunter ya está instalado, exige actualización Git **fast-forward**, reinstala el paquete y termina con `db integrity` + `doctor`. Nunca hace `reset --hard`, merge forzado ni borra la configuración.

Consulta [docs/operations.md](docs/operations.md) para instalación detallada, configuración, scheduler, mantenimiento, backups y recuperación.

## Qué hace DealHunter

- **Historial de precios**: conserva observaciones por proveedor/tienda/producto y su procedencia por run.
- **Price Intelligence**: clasifica `NEW_LOW`, `REAL_DEAL`, `GOOD_PRICE` y calcula `deal-score-v1` con histórico demostrable.
- **Comparación multiprovider**: Rappi y Uber Eats conservan identidad raw separada.
- **Alertas y Watchlist**: motor local con vista Web de sólo lectura.
- **Web local**: Flask + Jinja + HTMX + Bootstrap, assets vendorizados y sin CDN en runtime.
- **Seguridad local**: POST mutable con CSRF, SecretStore Fernet opt-in y ausencia de fallback débil para secretos.
- **Schema actual**: SQLite v17; las migraciones son automáticas y generan backup previo al subir de versión.

### Límites importantes

- La identidad raw `(provider, store_id, product_id)` sigue siendo autoridad.
- El matching canónico de producto continúa **shadow/experimental**; la canonicalización automática está desactivada.
- Los datos dependen de la ubicación configurada; cambiar de zona no borra histórico y puede afectar comparabilidad.
- La Web se vincula por defecto a `127.0.0.1` y no se expone automáticamente a la LAN.

## Documentación mantenida

El README es el punto de entrada. La documentación vigente se reduce deliberadamente a referencias con una responsabilidad clara:

- [Operación](docs/operations.md): instalar, configurar, iniciar, actualizar, scheduler, mantener y recuperar.
- [Arquitectura](docs/architecture.md): límites y flujo del sistema.
- [Web](docs/web.md): arquitectura UI y límites de seguridad.
- [CLI](docs/cli.md): comandos para automatización/uso avanzado.
- [Base de datos](docs/database-schema.md): schema y migraciones.
- [Seguridad](docs/security.md): secretos, CSRF, archivos y runtime.
- [Desarrollo y releases](docs/development.md): entorno dev, gates y publicación.
- [Índice técnico](docs/README.md): referencias de dominio adicionales.

Los reportes de fases, experimentos y guías sustituidas se conservan en [`docs/archive/`](docs/archive/) y [`docs/audit/`](docs/audit/) **como evidencia histórica, no como instrucciones actuales**.

## Desarrollo

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m compileall -q src tests
pytest -q
```

En Termux, si se usa venv, créalo con `--system-site-packages` para reutilizar `python-cryptography` nativo. Ver [docs/development.md](docs/development.md).

## Privacidad y licencia

DealHunter no envía tu base de datos a un backend propio. Las sesiones persistentes son opcionales y se cifran localmente; no deben entrar en SQLite, `config.toml`, logs ni Git. Consulta [SECURITY.md](SECURITY.md) y [docs/security.md](docs/security.md).

Licencia: [MIT](LICENSE).
