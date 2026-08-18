# Descubrimiento Adaptativo (Adaptive Discovery)

En lugar de consultar ciegamente categorías estáticas o escanear IDs de manera incremental (lo cual detonaría bloqueos de IP masivos), DealHunter utiliza un sistema orgánico de "Cola de Palabras Clave" que evoluciona durante la ejecución.

## El Flujo Adaptativo

1. **Seed Keyword (Semilla):** El crawler inicia con palabras genéricas (ej. `leche`, `oferta`).
2. **Productos Descubiertos:** La API devuelve un lote de productos (ej. Leche Alpura).
3. **Categorías/Marcas Extraídas:** El script analiza los metadatos de la respuesta y extrae marcas y categorías (ej. `Lácteos`, `Alpura`).
4. **Nuevas Keywords:** Inyecta silenciosamente `Alpura` y `Lácteos` en la cola de peticiones futuras.
5. **Productos Nuevos:** Cuando llega el turno de consultar `Alpura`, descubre quesos y yogures que antes no aparecían bajo `leche`.
6. **Cálculo de Rentabilidad (Novelty Rate):** Se calcula qué tan útil fue la palabra clave:
   `novelty_rate = productos_completamente_nuevos / resultados_validos`
7. **Continuar / Detener:** Si el `novelty_rate` es alto, la cola sigue creciendo. Si el índice de saturación se alcanza, el algoritmo detiene la búsqueda de ese vertical.

## ¿Qué es la Saturación?
DealHunter se detiene cuando entra en estado `SATURATED`. Esto ocurre cuando las últimas 4 búsquedas arrojaron un `novelty_rate` menor al 3%. 

**Importante:** La saturación NO significa necesariamente que hayas descargado el 100% del catálogo absoluto del proveedor. Significa matemáticamente que seguir disparando consultas sólo está desperdiciando ancho de banda y devolviendo productos que ya tenías guardados.
