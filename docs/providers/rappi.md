# Rappi Verticals

El motor distingue los comportamientos e ingestas adaptativas basándose en la metadata del proveedor.

## Market
Comercios de supermercado y farmacias clásicos. Cuentan con catálogo completo, inventario amplio, y promociones tradicionales (NxM, descuentos porcentuales).

## Turbo
Vertical de ultra-conveniencia. Se identifica mediante metadata estructurada provista por Rappi, limitando las selecciones y priorizando respuesta de precio rápida.

## Restaurants
(`parent_store_type == restaurants`)
DealHunter soporta restaurantes con ciertas limitaciones (dado el formato cerrado de menús):
- Categorías estructuradas desde la API.
- Precios base de platillos.
- `stock` puede registrarse como `NULL` si el origen no proporciona cantidades absolutas (infinito lógico).
- Atributos dinámicos (Toppings). DealHunter reporta si un platillo puede ser alterado basándose exclusivamente en metadata, pero no almacena el árbol completo de combos y complementos (ya que varían asíncronamente en el carrito).
