# Contribuir a Rappi Deal Hunter

¡Gracias por tu interés!

1. **Privacidad Primero:** NUNCA subas archivos `rappi-deals.db`, `logs`, o coordenadas GPS exactas. Todo JSON que subas como ejemplo debe estar sanitizado y ubicado en `tests/fixtures/`.
2. **Entorno:** El código está pensado primariamente para Termux (CLI/Linux).
3. **Tests:** Cualquier cambio a las matemáticas de `discount_effective` debe venir acompañado de pruebas en `tests/test_discounts.py`.
4. **Rate Limiting:** No aceptamos Pull Requests que introduzcan evasión activa de Cloudflare u otros mecanismos agresivos de WAF.
