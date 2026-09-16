# Instalación y Setup en Termux (Android)

Esta guía cubre el entorno operativo de DealHunter en Termux. Herramientas de investigación pesada no forman parte del runtime normal.

## 1. Requisitos

- Android con Termux actualizado.
- Conectividad para instalar dependencias y para los providers que se habiliten.

## 2. Dependencias del entorno

```bash
pkg update && pkg upgrade
pkg install git python sqlite python-cryptography
```

`python-cryptography` es el backend seguro recomendado en Termux. DealHunter no degrada SecretStore a plaintext/base64/firma si `cryptography` no puede cargarse.

## 3. Clonar e instalar dependencias Python

```bash
git clone https://github.com/yorologo/DealHunter.git
cd DealHunter
pip install -r requirements.txt
```

En Termux, si `cryptography` ya proviene de `python-cryptography`, conserva el paquete nativo funcional. Verifica:

```bash
python -c "from cryptography.fernet import Fernet; print('cryptography OK')"
```

No uses un `LD_PRELOAD` global como solución permanente de DealHunter.

## 4. Permisos de los binarios

```bash
chmod +x bin/rappi-ofertas bin/rappi-historico bin/dealwatcher
```

## 5. Configuración local

Configura la ubicación una sola vez; el archivo queda fuera de Git:

```bash
./bin/rappi-ofertas config set lat TU_LATITUD
./bin/rappi-ofertas config set lng TU_LONGITUD
```

La configuración vive en `~/.config/dealhunter/config.toml` o bajo `XDG_CONFIG_HOME`. Un TOML malformado produce `CONFIG_ERROR`; no se sustituye silenciosamente por defaults.

La DB respeta este orden:

1. `RAPPI_DB_PATH`, si se define explícitamente.
2. Una DB legacy existente en `~/rappi-deal-hunter/rappi-deals.db`.
3. `${XDG_DATA_HOME:-~/.local/share}/dealhunter/rappi-deals.db` para instalaciones nuevas.

No es necesario `termux-setup-storage` para esos paths privados de Termux.

## 6. Smoke local

```bash
./bin/rappi-ofertas doctor
./bin/rappi-ofertas providers
```

## 7. Primer run real

```bash
./bin/rappi-ofertas discover --vertical general
```

El crawler exige ubicación efectiva y conserva `lat/lng` como provenance del run. Puedes usar `--lat/--lng` sólo para un override deliberado de una ejecución.

## 8. Web local

```bash
./bin/rappi-historico web --port 8765
```

Por defecto escucha en `127.0.0.1:8765`.

## 9. Scheduler

Configura ubicación y providers antes de habilitarlo. Consulta [SCHEDULER.md](SCHEDULER.md) para la cadencia, `flock`, `crond` y wake-lock.
