# Getting Started

Bienvenido a DealHunter. Para ejecutarlo localmente:

## Requisitos
- Python 3.10+
- (Recomendado) Entorno virtual o Termux en Android.

## Instalación
```bash
git clone git@github.com:yorologo/DealHunter.git
cd DealHunter
```

## Uso de la Interfaz Web
La forma más fácil de usar DealHunter es a través de su interfaz web:

```bash
bin/rappi-historico web --port 8765
```

Abre tu navegador en `http://127.0.0.1:8765`.

## Uso del CLI
Para extracción y exploración manual:
```bash
bin/rappi-ofertas discover --min-discount 30
bin/rappi-ofertas update
```
