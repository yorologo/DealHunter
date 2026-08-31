# Instalación y Setup en Termux (Android)

Esta guía explica la instalación de producción/usuario-final del entorno offline/CLI, excluyendo herramientas pesadas como Blutter requeridas únicamente para la fase de investigación.

## 1. Requisitos Iniciales
- Dispositivo Android con `Termux` (instalado preferiblemente vía F-Droid, NO Play Store).
- Conexión a internet estable.

## 2. Instalar Dependencias del Entorno
Ejecutar dentro de la terminal Termux:
```bash
pkg update && pkg upgrade
pkg install git python sqlite
```

## 3. Clonar Repositorio
```bash
git clone https://github.com/yorologo/DealHunter.git
cd rappi-deal-hunter
pip install -r requirements.txt
```

## 4. Configurar Permisos
Dar permisos de ejecución a los binarios:
```bash
chmod +x bin/rappi-ofertas
chmod +x bin/rappi-historico
```

*(Opcional)* Si usarás rutas del almacenamiento local, es probable que requieras `termux-setup-storage`. Actualmente, todo se guarda por defecto en la misma carpeta raíz del repositorio en formato `rappi-deals.db`.

## 5. Pruebas de Arranque (Test Run)
Haz una minería microscópica controlada que no te hará chocar con un rate limit:
```bash
./bin/rappi-ofertas doctor
```
Verifica que la base de datos se haya creado.

## 6. Primer Run Real
Escanea tu área. Alimenta tus coordenadas reales usando `--lat` y `--lng`. Si prefieres testear la funcionalidad `general` que recorre todos los verticales:
```bash
./bin/rappi-ofertas discover --vertical general --lat TU_LATITUD --lng TU_LONGITUD
```

## 7. Ejecución de Históricos (Day 2 onwards)
Al día siguiente, corre el comando anterior de nuevo. Al finalizar, audita los resultados reales:
```bash
./bin/rappi-historico deals
```
