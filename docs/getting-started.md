# Tutorial Paso a Paso (Getting Started)

Sigue estos pasos para ir desde cero hasta tu primer análisis de precios.

## Paso 1 — Instalar Termux
Si usas Android, descarga e instala **Termux** desde F-Droid. (Evita la Play Store, ya que la versión allí está desactualizada).

## Paso 2 — Instalar dependencias
Abre Termux y actualiza los repositorios, luego instala `git`, `python` y `sqlite`:
```bash
pkg update && pkg upgrade -y
pkg install git python sqlite -y
```

## Paso 3 — Clonar DealHunter
Descarga el código del repositorio:
```bash
git clone git@github.com:yorologo/DealHunter.git
cd DealHunter
```

## Paso 4 — Inicializar
Otorga permisos de ejecución a los binarios principales:
```bash
chmod +x bin/rappi-ofertas
chmod +x bin/rappi-historico
```

## Paso 5 — Elegir ubicación
DealHunter necesita saber en qué área geográfica buscar comercios. Busca en Google Maps una latitud y longitud representativa de la zona que quieres monitorear (por ejemplo `19.4326`, `-99.1332`). *Evita usar las coordenadas exactas de tu casa por privacidad si planeas compartir tus resultados.*

## Paso 6 — Primera búsqueda
Ejecuta el minero. Por defecto, buscará ofertas en el vertical `supermercado`, pero podemos forzarlo a buscar en farmacias o mascotas.
```bash
./bin/rappi-ofertas --lat 19.4326 --lng -99.1332 --vertical general
```
Verás en consola cómo descubre palabras clave, inspecciona comercios y guarda las métricas.

## Paso 7 — Interpretar resultado
Una vez que termine el comando, DealHunter imprimirá una tabla con las ofertas iguales o mayores al 50%. Estas ofertas son temporales y se acaban de guardar en `rappi-deals.db`.

## Paso 8 — Ejecutar histórico
Dado que esta es tu primera corrida, las ofertas podrían tener su "Precio original" inflado. Para auditar esto, usamos el visor histórico:
```bash
./bin/rappi-historico
```
*Aviso:* En tu primer día, es normal que la inmensa mayoría de los resultados aparezcan con estado `INSUFFICIENT_HISTORY`. El motor requiere un margen de tiempo empírico para establecer el precio base de un producto.

## Paso 9 — Siguientes ejecuciones
Repite el Paso 6 al día siguiente. 
Cada vez que corras `rappi-ofertas`, tu base de datos sumará nuevas observaciones. Tras un par de días, `rappi-historico` comenzará a etiquetar ofertas como `REAL_DEAL` o `NEW_LOW` con base en el desplome estadístico real, no en el marketing visual.
