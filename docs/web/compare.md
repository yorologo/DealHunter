# Cross-Store Compare

La vista de comparación de precios cruzados (`/compare`) expone la lógica de "Matching" del backend en el navegador.

## Funcionamiento
- **Querying:** La búsqueda es server-side (`LIKE` name/brand), invocada en tiempo real mediante `HTMX` (`hx-trigger="keyup changed delay:500ms"`).
- **Matching:** Agrupa productos equivalentes (`EXACT_MATCH`, `HIGH_CONFIDENCE_MATCH`, `FUZZY_MATCH`) bajo el mismo paraguas visual.
- **Best Store Metric:** Resalta con un trofeo (🏆) y color distintivo (verde) la tienda con el *menor precio actual*. El `hist_min` de otra tienda *nunca* desplaza esta decisión operativa de HOY.

## Componentes Técnicos
- **Tabla Responsive:** Expone Producto, Tienda, Precio, Diferencia vs Mejor Precio, Precio Unitario, STATUS general y Tipo de match.
- **Filtros limitados:** Por diseño, si "brand" falta en la BD, se respeta el comportamiento del core (no hay Fuzzy match).
- **Deep-linking:** Los resultados empujan estado a la URL (`hx-push-url="true"`) para que se puedan compartir los enlaces de comparación.

## Limitaciones Fase B
- En Mobile, si la tabla de múltiples columnas rompe, se requiere de un scroll horizontal (`table-responsive`), lo que puede ser menos óptimo que Cards, pero provee densidad de datos comparativa.
