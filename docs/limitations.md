# Limitaciones Conocidas

DealHunter es una herramienta heurística, por tanto debes estar al tanto de sus debilidades algorítmicas:

* **No garantiza catálogo absoluto:** El método `Unified Search` prioriza mostrar "lo más relevante" o "lo más buscado". Si un producto sumamente raro nunca se cruzó con nuestra cadena adaptativa de keywords, no será minado.
* **Depende de la disponibilidad regional:** DealHunter no te mostrará lo que ocurre en toda la ciudad. Los resultados están estrictamente limitados al radio de entrega dictado por la coordenada (`lat`, `lng`) que proveas.
* **Precios inestables:** El precio final en este tipo de apps puede verse afectado en runtime por tus propios cupones de cuenta, membresía (RappiPro), o costos de envío dinámicos. DealHunter rastrea el precio "de vitrina público".
* **Rate Limiting:** Si los servidores están bajo estrés o tu IP es detectada levantando ráfagas anómalas, las peticiones pueden rebotar y detener la cobertura de ese día.
* **Cambios en servicios remotos:** Al no ser una API oficial ni pública, cualquier cambio brusco en el Payload JSON de los servidores romperá la compatibilidad del `Normalizer` sin previo aviso.
* **El histórico exige paciencia:** Durante tus primeros 2-3 días de uso, todas las métricas históricas estarán ciegas (`INSUFFICIENT_HISTORY`). No hay atajos para recuperar el precio del pasado.
