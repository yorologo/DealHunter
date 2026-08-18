# Motor Matemático de Promociones

Rappi suele presentar la información de descuento dividida en "descuento de precio tachado" o "bundles/paquetes". El motor se encarga de estandarizarlos en el campo de base de datos final: `discount_effective`.

## 1. Descuento Directo por Precio
Aplica cuando el artículo tiene su campo `real_price` mayor al `price` (precio en carrito).

```python
discount_price = (1 - price / real_price) * 100.0
```

## 2. Promoción en Paquete (NxM)
Se extrae de la rama `discounts_bundle[deal][0]`. El arreglo nos indica cuánto pagas por cuánto te llevas.

* `units_condition` = Cuánto pagas.
* `promotion_value` = Cuánto te llevas.

```python
discount_promotion = (1 - units_condition / promotion_value) * 100.0
```

**Comprobaciones de la ecuación:**
* **2x1:** `(1 - 1/2) * 100 = 50.0%`
* **3x1:** `(1 - 1/3) * 100 = 66.67%`
* **3x2:** `(1 - 2/3) * 100 = 33.33%`
* **4x2:** `(1 - 2/4) * 100 = 50.0%`

## 3. Descuento Efectivo y Evitar Doble Conteo
El motor previene rigurosamente el conteo doble. Rappi a veces muestra que algo cuesta $10 y tachado $20, pero además le ponen etiqueta "2x1". Matemáticamente esto no significa que sea un 100% de descuento. 

```python
if discount_promotion > discount_price:
    discount_effective = discount_promotion
    discount_source = "bundle"
else:
    discount_effective = discount_price
    discount_source = "price"
```

El algoritmo confía en la mayor reducción provista, descartando la publicidad redundante.
