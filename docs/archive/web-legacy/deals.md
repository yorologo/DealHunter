# Opportunities (Deals)

La vista "Oportunidades" lista los mejores hallazgos basándose en el análisis algorítmico histórico.

Conceptualmente, es esencial no mezclar métricas:
- **Price Intelligence** (`NEW_LOW`, `REAL_DEAL`, `GOOD_PRICE`) clasifica cómo es el precio actual *contra el historial pasivo de la base de datos*.
- **Alerts** (`TARGET_PRICE`, `PRICE_DROP`, etc.) son *eventos proactivos emitidos temporalmente*.

La vista web Oportunidades se basa predominantemente en Price Intelligence empírica, omitiendo ofertas publicitadas que en la práctica igualan el precio usual.
