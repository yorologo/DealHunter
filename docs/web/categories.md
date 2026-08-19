# Categories Semantics
- En la base inicial, `query_term` se presentaba erróneamente como categoría principal.
- Ahora, `category_name` real proveniente del crawler (p.get("category_name")) se persiste en `products.category` (Schema v6).
- Si no existe categoría, el sistema hace fallback a 'Uncategorized' / 'Otros'.
