# Filtros Avanzados

Ejemplos de recetas comunes:

**>= 40% descuento:**
`rappi-ofertas --min-discount 40`

**Promociones >= 50%:**
`rappi-ofertas --min-promo-discount 50`

**Sólo 2x1:**
`rappi-ofertas --only-nxm`

**Menos de $500:**
`rappi-ofertas --max-price 500`

**Solo Chedraui:**
`rappi-ofertas --store "Chedraui"`

**Excluir Office Depot:**
`rappi-ofertas --exclude-store "Office Depot"`

**Farmacia y Supermercado:**
`rappi-ofertas --vertical farmacia --vertical supermercado`

**Producto específico:**
`rappi-ofertas --query "Leche Lala"`
