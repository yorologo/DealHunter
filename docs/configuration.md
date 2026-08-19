# Configuración DealHunter

La configuración se guarda en `~/.config/dealhunter/config.toml` o en la ruta definida por `XDG_CONFIG_HOME`.

## Jerarquía

1. CLI Arguments (Máxima prioridad)
2. Perfil (`--profile nombre`)
3. Global (`config.toml`)
4. Defaults internos

## Comandos

```bash
rappi-ofertas config show
rappi-ofertas config set min_discount 40
rappi-ofertas config get min_discount
rappi-ofertas config reset
```

## Ejemplo TOML

```toml
min_discount = 30
max_requests = 1000

[profiles.despensa]
min_discount = 40
vertical = ["supermercado"]
query = ["leche", "café"]

[profiles.farmacia]
vertical = ["farmacia"]
min_discount = 50
```
