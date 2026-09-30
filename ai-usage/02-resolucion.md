# Sesión 02: resolución nombre → QID

## Prompt del candidato
"Quita el PDF, añade gitattributes y sigue con el paso 2."

## Qué hizo la IA
- Añadió `.gitattributes` para fijar los finales de línea en LF.
- No pudo quitar el PDF del historial: la herramienta bloqueó la reescritura de git por considerarla destructiva. Queda pendiente de que lo haga el candidato.
- Implementó `wikidata.py`: caché en disco por petición, User-Agent identificable, reintentos con backoff y modo `--offline`.
- Implementó `resolve.py`: búsqueda de candidatos con wbsearchentities en inglés y español, hechos de cada candidato por SPARQL, puntuación, decisión y overrides.
- Resultado de la primera ejecución completa: 484 matched, 14 ambiguous y 2 not_a_person. Los 7 pares seudónimo/nombre real se detectan solos como QIDs compartidos.

## Errores detectados y corregidos durante la validación
- **Almudena Grandes salía como `partial`.** La API informa como coincidencia del alias largo ("Almudena Grandes Hernández") aunque la etiqueta coincida exactamente. Se corrigió para comprobar primero la etiqueta, y se añadió un test.
- **Homer resolvía a Winslow Homer.** El Q6691 tiene P31 = Q21070568 ("humano cuya existencia se discute") y no Q5, así que el filtro de humanos lo descartaba. Se propone ajustar la regla.

## Revisión manual de la IA
- Revisó los 27 nombres de una sola palabra: todos correctos (Colette, Azorín → José Martínez Ruiz, Adonis, Stendhal, Rumi…).
- De los 13 ambiguos restantes, en todos el mejor candidato es el correcto. La regla de margen es demasiado conservadora cuando hay homónimos poco conocidos que también son escritores (John Milton padre, Robert Browning el bizantinista…).
