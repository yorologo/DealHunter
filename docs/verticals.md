# Verticales y Compartimentación

Un **vertical** es un contexto de búsqueda (un departamento lógico). DealHunter soporta los siguientes perfiles de extracción:
* `supermercado`
* `farmacia`
* `mascotas`
* `bebe`
* `higiene`
* `hogar`
* `tecnologia`
* `general` (Itera secuencialmente todos los anteriores)

## ¿Por qué separar la búsqueda?
Si mezcláramos todos los dominios desde el inicio, el inventario gigante de un *Supermercado* opacaría rápidamente a las tiendas menores. El algoritmo adaptativo se llenaría de marcas de comida y alcanzaría la condición de *Saturación* mucho antes de siquiera tropezar con la marca de unas croquetas especializadas.

Al usar verticales, cada perfil mantiene su propio estado de saturación y cola de palabras:
```text
Ejecución: --vertical general

1. Supermercado comienza...
2. Supermercado extrae 3,000 items. 
3. Supermercado entra en SATURATED y se detiene.

4. Tecnología comienza... (Su cola está intacta)
5. Tecnología extrae 120 items de MacStore y Lumen.
6. Tecnología entra en LOW_COVERAGE. Fin.
```

Gracias a los verticales, las farmacias y tiendas de tecnología pueden florecer independientemente sin ser devoradas por la marea de abarrotes.
