# 02: Resolución nombre → QID

## Qué pedí
Implementar el cliente de Wikidata con caché y la resolución de los 500 nombres, y presentarme los casos dudosos antes de dar nada por cerrado.

## Qué implementó la IA
- Un cliente HTTP con caché en disco, modo offline y reintentos.
- Búsqueda de candidatos en inglés y español, señales por SPARQL (humano, perfil literario, obras P50, sitelinks), puntuación y decisión.

## Resultado de la primera ejecución
- 484 `matched`, 14 `ambiguous` y 2 `not_a_person`.
- Los 7 pares de seudónimos se detectaron solos porque resuelven al mismo QID.

## Casos dudosos (analizados por la IA, revisados por mí antes de decidir)
- **Los 14 ambiguos.** En 13, el candidato elegido era correcto; la regla de margen era demasiado conservadora con homónimos menores que también escriben (el padre de John Milton, un bizantinista llamado Robert Browning…).
- **El caso incorrecto: Homer → Winslow Homer.** El Homero de Wikidata está clasificado como «humano cuya existencia se discute», no como «humano».
- **Los nombres de una sola palabra**: todos correctos.

## Problema corregido
Almudena Grandes salía como coincidencia parcial: la API informaba del alias largo aunque la etiqueta coincidiera. Se corrigió y se añadió un test.
