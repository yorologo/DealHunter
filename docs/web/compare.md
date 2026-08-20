# Compare

La sección de comparativas se divide conceptualmente en dos mecanismos:

### Manual Compare
Selección manual iniciada desde el buscador (`search` → `select` → `compare`).

### Anchor Compare
Comparación dinámica desde la vista *Product Detail*. Utiliza la entidad base (`store_id` + `product_id`) como ancla, consulta candidatos (reducidos por base de datos), ejecuta el `matcher` (precision-first), y extrae el subconjunto de equivalentes válidos para presentar la tienda con el mejor precio base y por unidad (`best_store`).

Se asume la limitación: Es preferible perder un match legítimo si el fingerprint o nombre varían excesivamente, antes que mezclar productos dispares como si fueran el mismo.
