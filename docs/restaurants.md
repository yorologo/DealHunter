# Restaurantes en DealHunter

DealHunter v2.2 integra soporte inicial para el análisis de menús y promociones de **Restaurantes** en Rappi.

## Cómo funciona
A diferencia de los catálogos de supermercado, los restaurantes se agrupan bajo el `parent_store_type: "restaurants"`. 
Dado que el endpoint de búsqueda unificada `unified-search` retorna los platillos del menú con una estructura virtualmente idéntica a los productos de mercado (`price`, `real_price`, `name`, `discounts_bundle`), DealHunter reutiliza exitosamente su **Discount Engine** y modelo de histórico para el registro de platillos.

## Comandos

Para buscar ofertas en restaurantes, utiliza el comando `restaurants`:

```bash
rappi-ofertas restaurants --query "hamburguesa"
```

También puedes filtrar por un restaurante específico usando `--restaurant` (alias de `--store`):

```bash
rappi-ofertas restaurants --restaurant "Mc Donald's" --query "combo"
```

## Compatibilidad de Filtros
Todos los filtros numéricos y semánticos son compatibles con restaurantes:
- `--min-price`, `--max-price`
- `--min-discount`, `--max-discount`
- `--promo`, `--only-nxm`
- `--top`, `--sort`, `--format`

## Modelo de Datos y Limitaciones
El modelo actual (`Product`, `Store`, `Observation`) se reutiliza de forma limpia. 
- **Stock:** Si un restaurante omite el campo `stock` pero indica `in_stock: true` o `is_available: true`, DealHunter asume automáticamente un stock disponible mínimo (1) para conservar el registro.
- **Modificadores/Extras:** Algunos platillos (`has_toppings: true`) requieren modificadores cuyo precio altera el total. DealHunter registrará el **precio base** tal y como viene en el catálogo. No se hace resolución dinámica de modificadores en esta versión.
- **Promociones:** Promociones de platillo (Directos o NxM) son interpretadas nativamente. Promociones "del carrito" (ej. -$50 en la orden entera) no se imputan al precio unitario del platillo para evitar corromper el histórico.

## Histórico
Los platillos mantienen un `product_id` persistente otorgado por el backend, lo cual significa que se pueden acumular precios históricos a lo largo de los días y las observaciones pueden marcar `NEW_LOW` y `REAL_DEAL` tal como se hace en supermercados.
