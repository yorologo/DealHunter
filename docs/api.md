# API Pública Detectada

> **Public/read-only observed endpoint**

El crawler actualmente funciona explotando el motor de búsqueda universal de Rappi mediante POST requests genéricas y sin autenticación, simulando un dispositivo final consultando catálogo abierto.

## Endpoint: Unified Search
* **Host:** `services.mxgrability.rappi.com`
* **Método:** `POST`
* **Path:** `/api/pns-global-search-api/v1/unified-search`

### Request Header Obligatorio
* `Accept`: `application/json`
* `Content-Type`: `application/json`
* `User-Agent`: (Recomendable: Identificador móvil común u OkHttp para prevenir rechazo inmediato del WAF).

### Payload (Body JSON)
```json
{
  "query": "leche",
  "lat": 19.4326,
  "lng": -99.1332,
  "limit": 1000
}
```

### Respuesta Estructurada (Extracto simplificado)
```json
{
  "stores": [
    {
      "store_id": "990006029",
      "store_name": "City Market",
      "parent_store_type": "market",
      "products": [
        {
          "product_id": "12345",
          "name": "Leche Entera",
          "price": 25.0,
          "real_price": 28.0,
          "stock": 10,
          "in_stock": true,
          "discounts_bundle": {
             "deal": [
                {
                   "promotion_value": 3,
                   "units_condition": 2,
                   "label": "Agregue 3, pague 2"
                }
             ]
          }
        }
      ]
    }
  ]
}
```

### Comportamiento del WAF (Web Application Firewall)
- **Timeouts recomendados**: Mínimo 3 segundos entre peticiones (`time.sleep(3)`).
- **HTTP 429**: Límite estándar de tasa de refresco cruzado. El algoritmo local captura esta excepción y declara el "vertical" actual como `RATE_LIMITED` cerrando el barrido para evitar ban.
- **HTTP 1015 (Cloudflare)**: Ocurre ante ataques de burst. Penaliza la IP temporalmente. No hay `bypasses` implementados ni se recomienda evadir esta protección.
