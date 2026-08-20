# Product Normalization

El pipeline de normalización procesa y limpia cadenas de nombres para extraer información estructurada y estandarizarla, permitiendo la comparación inter-tienda y cálculo de precios unitarios.

## Entidades Estructuradas extraídas
- `normalized_name`: Nombre canónico limpio.
- `brand`: Marca del producto.
- `quantity`: Cantidad numérica extraída (ej. 500).
- `unit`: Unidad (ej. ml, g).
- `pack_count`: Tamaño del paquete (ej. 12 para un 12-pack).
- `normalized_quantity`: Cantidad adaptada al sistema estándar.
- `normalized_unit`: Unidad estándar correspondiente.
- `fingerprint`: Identificador único conservador.
- `unit_price`: Precio real por unidad base estandarizada.

## Conversiones Soportadas

DealHunter estandariza automáticamente las unidades para facilitar su comparación:
- `g` → `kg` (ej. 500 g → 0.5 kg)
- `ml` → `L` (ej. 500 ml → 0.5 L)
- `mg` → `kg`

## Unit Price

Calculado dinámicamente como el cociente entre el precio final (`price`) y el producto de `normalized_quantity * pack_count`.
Ejemplo: Un 6-pack de cervezas de 355 ml a $120 MXN genera un precio unitario sobre `2.13 L` de volumen.
