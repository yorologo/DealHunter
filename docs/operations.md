# Operación: instalar, configurar, actualizar y recuperar

Ésta es la guía operativa canónica. Si otra guía histórica contradice este archivo o el README, prevalecen **README + este documento + código ejecutable**.

## 1. Instalación desde cero en Termux

### Requisitos

- Android + Termux actualizado desde una fuente soportada por Termux.
- Acceso a Internet para clonar e instalar dependencias.
- `git` para obtener el repositorio.

```bash
pkg install git
git clone https://github.com/yorologo/DealHunter.git
cd DealHunter
git checkout main
./install.sh
```

`install.sh` es idempotente y deliberadamente pequeño. Comprueba Python 3.11+, instala únicamente paquetes Termux faltantes (`python`, `python-cryptography`, `git`, `flock`/`util-linux`, `cronie` según sea necesario), ejecuta `pip install .` y hace smoke tests locales. **No ejecuta `pkg upgrade` ni modifica la configuración personal.**

En Android, `cryptography` se obtiene del paquete nativo `python-cryptography`; `pyproject.toml` evita instalar un wheel pip incompatible sobre Termux.

### Otros Linux

El instalador no crea entornos Python ocultos. Fuera de Termux úsalo dentro de un venv:

```bash
python3 -m venv .venv
. .venv/bin/activate
./install.sh
```

Para desarrollo usa `pip install -e '.[test]'` como se documenta en `development.md`.

## 2. Configuración mínima

La Web puede arrancar sin credenciales. Para adquirir datos sólo son obligatorias las coordenadas de entrega `lat/lng`.

Ruta recomendada para un usuario nuevo:

1. Ejecuta `dealhunter web`.
2. Abre `http://127.0.0.1:8765`.
3. Ve a **Admin → Settings**.
4. Guarda `lat` y `lng` válidos.
5. Ejecuta un sync desde Catalog Sync o por CLI.

Alternativa CLI:

```bash
dealhunter config set lat TU_LATITUD
dealhunter config set lng TU_LONGITUD
dealhunter config show
dealhunter doctor
```

La configuración vive fuera del repositorio, bajo `XDG_CONFIG_HOME` o `~/.config/dealhunter`. Los secretos no se guardan en `config.toml`.

### Configuración opcional

- **Rappi session**: Admin → **Cuentas / Proveedores** es la autoridad UX. En Android/Termux, **Configurar desde este teléfono** genera por POST un bookmarklet efímero (5 min) que captura voluntariamente el `Authorization` de la sesión Rappi y vuelve únicamente por loopback al Flask local; la credencial se guarda cifrada mediante SecretStore y se valida con `get_account_status()`. El método **PC / navegador** existente permanece disponible desde la misma tarjeta.
- **Uber Eats**: Admin → **Cuentas / Proveedores** muestra estado local del profile/runtime. Si indica `NEEDS_LOGIN`, ejecuta `dealhunter uber setup` en Termux y luego usa **Comprobar sesión** en la Web. El profile por sí solo permanece `UNVERIFIED` hasta esa comprobación.
- **Membresías**: `dealhunter membership rappi_pro ...` / `uber_one ...` sólo afectan elegibilidad/comparación.
- **Providers**: pueden habilitarse/deshabilitarse por separado.

## 3. Iniciar y comprobar

```bash
dealhunter doctor
dealhunter web
```

La Web inicializa/migra SQLite antes de servir y escucha en `127.0.0.1:8765`. En Termux intenta adquirir wake lock si `termux-wake-lock` está disponible. El wake lock es compartido por la app Termux y no se libera automáticamente al cerrar DealHunter.

`Admin → Runs → Iniciar Crawler` también requiere `lat/lng` válidos. El inicio usa POST + CSRF y, tras reservar el run, redirige a su detalle. El progreso real queda persistido en SQLite: Zone Inventory pasa de discovery indeterminado a progreso por merchants cuando conoce el total; Search Discovery no fabrica porcentaje si el trabajo sigue siendo dinámico. Recargar la página no detiene el crawler ni pierde su progreso.

Comandos de salud:

```bash
dealhunter db status
dealhunter db integrity
dealhunter runs --last 10
```

## 4. Scheduler opcional

DealHunter administra sólo sus propias líneas de crontab y conserva las ajenas.

```bash
# Requiere lat/lng configurados
dealhunter scheduler enable
crond
dealhunter scheduler status
```

Cadencia administrada:

- Rappi: `07:00`, `10:00`, `13:00`, `19:00`.
- Uber Eats: `07:30`, `10:30`, `13:30`, `19:30`.

Ambos usan el mismo `flock`; nunca deben correr simultáneamente. Cada job ejecuta mantenimiento operacional acotado, sync y DealWatcher. Los logs viven fuera del repositorio.

Para retirarlo:

```bash
dealhunter scheduler disable
```

Tras reiniciar Android, `crond` puede requerir inicio manual. DealHunter no instala un servicio de sistema adicional para ocultar esta limitación de Termux.

## 5. Actualizar de forma segura

Para instalaciones de release, `main` es la rama soportada. Antes de actualizar no debe haber cambios locales sin guardar.

### Transición única desde v3.3.1

El tag `v3.3.1` es anterior a `update.sh`, por lo que esa release necesita una sola actualización manual equivalente al updater:

```bash
cd DealHunter
dealhunter db backup
git fetch --tags origin main
git merge --ff-only origin/main
./install.sh
dealhunter db integrity
dealhunter doctor
```

No uses `git pull` sin política ni `reset --hard`: el `merge --ff-only` debe rechazar cualquier divergencia.

### Desde v3.4.0 en adelante

```bash
cd DealHunter
./update.sh
```

El updater aplica este orden:

1. exige rama `main` y worktree limpio;
2. si DealHunter ya está instalado, crea un backup SQLite verificado;
3. `git fetch --tags origin main`;
4. rechaza divergencias y sólo acepta `fast-forward`;
5. reinstala el checkout mediante `./install.sh`;
6. ejecuta `dealhunter db integrity` y `dealhunter doctor`.

No ejecuta `git reset --hard`, no fuerza merges, no borra datos y no restaura automáticamente un backup. Si algo falla, conserva el SHA anterior en el mensaje de error y deja el backup disponible para recuperación explícita.

Si falla una comprobación después del fast-forward, el updater imprime un rollback temporal y reversible:

```bash
git switch --detach SHA_ANTERIOR
./install.sh
# cuando quieras volver a la rama soportada
git switch main
```

Esto reinstala el código anterior sin reescribir `main`. No uses `reset --hard` para resolver una actualización fallida.

### Actualizar manualmente (desarrolladores)

Los desarrolladores en `develop` deben usar Git directamente y volver a instalar editable cuando corresponda. `update.sh` se niega a operar fuera de `main` a propósito.

## 6. Mantenimiento

### Mantenimiento operacional

```bash
dealhunter maintenance run
```

Rota logs/diagnósticos administrados. No purga el histórico comercial de SQLite.

### Backup e integridad

```bash
dealhunter db backup
dealhunter db integrity
```

Los backups SQLite se reabren, pasan `PRAGMA integrity_check` y deben conservar la misma versión de schema de la fuente antes de ser aceptados.

`vacuum` existe para mantenimiento explícito:

```bash
dealhunter db vacuum
```

No se ejecuta automáticamente durante instalación/update porque puede ser costoso y no es necesario para la operación normal.

## 7. Recuperación ante errores

### La Web no inicia

```bash
dealhunter doctor
dealhunter db integrity
```

Si falla `cryptography` en Termux:

```bash
pkg install python-cryptography
python -c 'from cryptography.fernet import Fernet; print("ok")'
```

No uses un fallback plaintext/base64 ni `LD_PRELOAD` global para “arreglar” SecretStore.

### SQLite está dañada

1. Detén Web, crawler y scheduler para evitar writers.
2. Ejecuta `dealhunter db status` y conserva la DB dañada; no la sobreescribas a ciegas.
3. Identifica un `.bak` creado por DealHunter.
4. Copia la DB dañada a un nombre de cuarentena.
5. Restaura explícitamente el backup sobre la ruta reportada por `db status`.
6. Ejecuta `dealhunter db integrity` y luego `dealhunter doctor`.
7. Al siguiente arranque, una DB antigua se migra automáticamente y se vuelve a respaldar antes del cambio de schema.

La restauración no está automatizada como un comando destructivo: elegir qué backup reemplaza la DB activa requiere una decisión humana explícita.

### El scheduler no corre

```bash
dealhunter scheduler status
command -v crontab
pgrep -af crond || crond
```

Comprueba además que `lat/lng` sigan configurados y que Android no haya detenido Termux.

### Rate limit / WAF

DealHunter no evade 401/403/429 ni WAF agresivamente. Un run parcial conserva observaciones ya confirmadas y evita reconciliación destructiva. Espera y reintenta más tarde si el proveedor limita temporalmente.

## 8. Releases

Las releases son **source-based**: GitHub ya genera los archives del tag y DealHunter se instala desde el checkout mediante `install.sh`. No se mantiene un segundo artefacto binario mientras no exista una necesidad demostrada.

Una release válida debe tener:

- versión coherente en runtime, README y CHANGELOG;
- tag anotado `vX.Y.Z` sobre el SHA publicado;
- GitHub Release correspondiente;
- CI verde en Python 3.11 y 3.14 sobre el SHA promovido;
- notas de migración/configuración si cambian schema o requisitos;
- `install.sh`/`update.sh` funcionales desde el tag.

El proceso de desarrollo/publicación está en `development.md`.
