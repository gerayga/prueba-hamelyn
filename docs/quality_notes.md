## 7. Análisis manual

> Esta sección está escrita a mano (`docs/quality_notes.md`); el resto del informe se genera desde los datos.

### 7.1 Qué se ha revisado y cómo

| Revisión | Alcance | Resultado |
|---|---|---|
| Casos `ambiguous` de la primera ejecución (hoy en §2.3 y §2.4) | 14/14 | 13 correctos (resueltos después con la regla de dominancia) y 1 incorrecto: Homer → Winslow Homer. Se corrigió aceptando Q21070568 («humano cuya existencia se discute») como persona. |
| Nombres de una sola palabra (Homer, Colette, Azorín, Adonis…) | 27/27 | Todos correctos. Azorín resuelve a José Martínez Ruiz (Q443403), Adonis al poeta sirio. |
| Seudónimos / nombres reales del seed | 7 pares | Los 7 resuelven al mismo QID de forma automática (§2.1). |
| Resueltos por alias (§2.5) | todos | Correctos: variantes de transliteración (Dostoevsky/Dostoyevsky, Forough/Forugh), formas cortas (Guimarães Rosa, Eça de Queirós) y seudónimos. |
| Muestra aleatoria (§6) | 20 filas | **20/20 QIDs correctos.** Fechas de nacimiento comparadas con fuentes de referencia: 19/20 coinciden. La que no coincidía era Ismat Chughtai (ver 7.2). |
| Diff entre ejecuciones al cambiar reglas | 500 filas | Cada cambio de reglas se validó comparando la resolución antes y después; solo cambian los casos previstos (ver `ai-usage/`). |
| Reproducibilidad | exports completos | `run --offline` produce CSV idénticos byte a byte a los commiteados (`tests/test_pipeline.py`). |

La revisión de QIDs y fechas la hizo el asistente de IA con conocimiento general, y el candidato la supervisó (ver `ai-usage/`). No es una verificación contra una fuente externa independiente, y así se declara.

### 7.2 Casos dudosos comentados

- **Mary Beard** (único override). Hay dos candidatas con notoriedad parecida: la clasicista británica (38 sitelinks) y la historiadora estadounidense Mary Ritter Beard (28). La regla no decide sola y se resolvió manualmente por contexto: el seed agrupa divulgación contemporánea (Harari, Diamond, Sagan). La justificación queda en `data/overrides.csv`.
- **Ismat Chughtai.** Wikidata tiene 5 fechas de nacimiento de rango normal (1911, 1915 y 1925, con días distintos). El desempate original («la primera que devuelve el API») daba 1911. Se cambió a «más referencias, sin contar P143 (importado de Wikipedia)», y ahora da 1915-08-15. El año coincide con la fuente de referencia (21-08-1915); el día sigue discutido. Queda marcado en `conflicting_fields`. El mismo cambio corrigió la fecha de muerte de Sadegh Hedayat (04-04 → 09-04-1951).
- **Murasaki Shikibu.** Aparece en la comprobación «vida > 105 años» (970–1100), pero es un efecto de la precisión, no un error. El valor preferente de muerte es `1100` con precisión de siglo, es decir, «siglo XI». Por eso las fechas deben leerse siempre junto con `*_precision`.
- **Homero, Laozi, Safo y otros autores antiguos.** Las fechas son aproximaciones con precisión de siglo o década y, en varios casos, con muchos valores alternativos en Wikidata. Se toma el de rango preferente.
- **Robert Galbraith → J. K. Rowling.** Existe en Wikidata una entidad «Robert Galbraith» (juez escocés) con el nombre exacto. Gana Rowling porque el alias coincide, es escritora y tiene 181 sitelinks frente a 2. Es la decisión correcta para una base de datos de autores de libros, pero depende de la regla de notoriedad (ver 7.3).
- **Autores de no ficción y ciencia** (Hawking, Sagan, Goodall, Kahneman…). Se aceptan como autores porque tienen obras con P50 o una ocupación de escritor. Jane Goodall se resuelve a la primatóloga y no a la escritora australiana homónima (Jane R. Goodall, 4 sitelinks).

### 7.3 Limitaciones

1. **Una sola fuente.** Todo sale de Wikidata. Hereda sus sesgos de cobertura: los autores occidentales y canónicos están mejor descritos. Las 500 filas del seed son autores conocidos, así que la cobertura del 100 % no se extrapola a una lista de autores poco conocidos.
2. **La notoriedad como desempate.** La puntuación y la regla de dominancia favorecen al homónimo más famoso. Es lo correcto para este seed, pero fallaría si la lista incluyera a un autor menor con el mismo nombre que otro famoso. Sin contexto adicional (por ejemplo, un ISBN o un título de obra en el seed) no se puede distinguir.
3. **Pesos heurísticos no calibrados.** Los pesos (0,40 nombre / 0,35 perfil literario / 0,25 notoriedad) y los umbrales se ajustaron observando este seed, no contra un conjunto etiquetado. La mitigación es que cada decisión es trazable (`candidates`, `seed_resolution.note`) y los casos límite se listan en este informe.
4. **Búsqueda solo en inglés y español.** Todos los nombres del seed están en alfabeto latino. Para nombres en otras escrituras habría que añadir idiomas de búsqueda.
5. **Instantánea.** Los datos reflejan Wikidata en la fecha de descarga (`retrieved_at`). Una ejecución online posterior puede dar resultados distintos; la caché permite reproducir exactamente esta versión.
6. **Selección de valores únicos.** Para lugares con varios valores sin rango preferente se elige el de menor QID. Es determinista pero arbitrario, y queda marcado en `conflicting_fields`.
7. **Lista de no-personas escrita a mano** (`Anonymous`, `Various Authors`…). Una lista nueva podría traer otros genéricos («Anónimo», «VV. AA.», «Unknown»). Los más comunes ya están incluidos.
8. **Seudónimos.** Cada fila del seed apunta a la persona real. El seudónimo se conserva como nombre (`author_names`, `kind='pseudonym'`), pero no como entidad propia. Si se necesitara atribuir obras al seudónimo, habría que modelarlo aparte.
9. **Etiquetas en inglés.** Nombres de lugares, ocupaciones e idiomas se guardan en inglés, con respaldo en `mul` y español. `label_es` sí se guarda para el nombre del autor.
