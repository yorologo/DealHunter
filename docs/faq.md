# Preguntas Frecuentes (FAQ)

## ¿Necesito acceso Root?
No. El script se ejecuta en entorno de usuario normal dentro de Termux o cualquier distribución Linux.

## ¿Necesito Shizuku?
No. Shizuku y `uiautomator` se utilizaron únicamente en las primeras fases de investigación para entender la interfaz gráfica de Rappi. El código actual opera limpiamente por red.

## ¿Necesito tener Rappi abierto o iniciar sesión?
No. Las consultas se realizan sin sesión (`read-only`), simulando el comportamiento de un usuario que aún no ha introducido sus credenciales en el explorador público.

## ¿DealHunter compra productos?
Absolutamente no. Es un motor de minería pasivo. No cuenta con capacidades transaccionales, ni carrito de compras, ni llaves de pago.

## ¿Guarda mis credenciales?
No las guarda ni las pide. 

## ¿Por qué no aparecen todas las tiendas?
El catálogo es radicalmente dinámico y depende de tus coordenadas (`--lat` y `--lng`). Las tiendas aparecen o desaparecen dependiendo del horario de servicio, demanda de repartidores y el radio interno que Rappi asigne a tu ubicación.

## ¿Por qué una tienda tiene pocos productos?
Algunas tiendas de conveniencia o nicho (como farmacias de barrio) no tienen su catálogo enteramente subido, o devuelven pocos resultados al buscar palabras generalistas. DealHunter combate esto agregando automáticamente el nombre de la tienda pobre a la cola de búsqueda para forzar que devuelva su inventario.

## ¿Por qué una promoción 3x2 no aparece con 50% de descuento?
Porque matemáticamente no lo es. Un 3x2 implica que pagas 2 productos y te llevas 3. El descuento equivalente es del 33.33%. DealHunter es riguroso con la aritmética del ahorro real.

## ¿Por qué el histórico dice `INSUFFICIENT_HISTORY`?
Para validar que una caída de precio es real, el motor exige que la oferta madure (por defecto, > 24 hrs de registro). Si tu base de datos fue creada hoy, todos los productos tendrán este estatus. Vuelve a escanear mañana.

## ¿Cuántos días necesito?
Se recomienda correr el crawler al menos una vez al día durante una semana. A partir del tercer día, los precios base estarán correctamente establecidos.

## ¿Qué pasa si recibo HTTP 429 o RATE_LIMITED?
El WAF (Cloudflare/Rappi) ha notado tu volumen de peticiones y te ha puesto en tiempo fuera temporal. Detén el script y espera unos minutos. No intentes evadir agresivamente este bloqueo.

## ¿Puedo ejecutar DealHunter diariamente?
Sí, usar *cron* en Linux o Termux para automatizar una pasada a mediodía es el flujo de trabajo ideal para construir la base SQLite.

## ¿Se puede usar fuera de México?
Aunque la API (`services.mxgrability.rappi.com`) está orientada a la infraestructura MX/Grability, la arquitectura subyacente de búsqueda unificada suele compartirse en LATAM. Puedes intentarlo proporcionando latitudes de otro país, pero no se garantiza su funcionamiento.
