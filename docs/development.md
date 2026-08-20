# Development Guide

## Arquitectura y Lógica de Dominio
Cualquier nueva lógica analítica debe residir dentro del core (`src/dealhunter`), para que pueda ser compartida por Web y CLI. 
La web está pensada como una *Thin Web Layer* de visualización que NO duplica normalización ni deducciones algorítmicas.

## Seguridad Continua
Toda ruta mutable introducida en Web debe usar `POST` con protección estricta contra `CSRF` e incluir su respectivo Unit Test en `tests/test_admin.py` o `tests/test_web.py`.
Evite servir o almacenar `.bak`, `db`, secrets, o PII dentro de estáticos/logs.

## Agentes 
Revise `AGENTS.md` como la fuente narrativa fundamental de reglas técnicas para agentes autónomos.
