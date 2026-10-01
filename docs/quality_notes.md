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

### 7.3 Sensibilidad de los parámetros

Los pesos de la puntuación (0,40 nombre / 0,35 perfil literario / 0,25 notoriedad) son heurísticos. Para saber si condicionan el resultado, se recalculó la resolución de las 498 filas con otras configuraciones (`python scripts/sensitivity.py`, offline):

- **Repartos razonables** (0,50/0,30/0,20 · 1/3 cada uno · 0,60/0,20/0,20 · 0,30/0,30/0,40): eligen exactamente los mismos 498 autores.
- **Barrido completo** (171 combinaciones en pasos de 0,05): **493 de 498 filas resuelven siempre al mismo autor.** Las 5 restantes:

| Fila | Cuándo cambia | Por qué |
|---|---|---|
| Robert Galbraith | notoriedad ≤ 0,20 | gana el juez escocés homónimo, que tiene el nombre exacto |
| Nguyễn Du | notoriedad ≥ 0,70 | gana Ho Chi Minh, por pura fama |
| Samuel Clemens, Mary Ann Evans | nombre ≥ 0,85 | ganan homónimos desconocidos en lugar del seudónimo famoso |
| **Jane Goodall** | perfil literario claramente por encima de la notoriedad (p. ej. 0,40/0,40/0,20) | **caso límite real**: la primatóloga tiene libros pero no figura como «escritora», y compite con una escritora australiana homónima. Los pesos actuales están cerca de su frontera; hoy se resuelve por dominancia (122 frente a 4 sitelinks) |

- **Umbral** (0,5–0,7), **margen** (0,10–0,20) y **dominancia** (2×–5×) no cambian ninguna decisión en esos rangos. Con valores más estrictos, algunos casos pasan a revisión manual, pero ninguno cambia de autor.

**Por qué el factor de dominancia es 5×.** En las 13 filas donde el mejor candidato saca menos de 0,15 de ventaja al segundo, la proporción de sitelinks entre ambos se reparte en dos grupos muy separados:

| Grupo | Filas | Proporción de sitelinks (elegido / 2º) |
|---|---|---|
| Homónimo claramente menor | Galbraith → Rowling (90×), Henry James (33×), John Milton (31×), W. B. Yeats (31×), Jane Goodall (30×), Mario Benedetti (23×), Primo Levi (23×), James Baldwin (20×), Samuel Johnson (12×), Bruno Schulz (11×), Robert Browning (9,8×), Nguyễn Du (9,2×) | **≥ 9,2×** |
| Ambigüedad real | Mary Beard (38 frente a 28) | **1,4×** |

Cualquier factor entre 1,4× y 9,2× produce exactamente el mismo resultado. Se eligió 5×, que cae en medio de ese hueco. El valor exacto no es una decisión crítica: aunque saliera del rango, ningún autor cambiaría; solo variaría cuántos casos se aceptan automáticamente y cuántos van a revisión manual. El riesgo de la regla es el mismo sesgo de notoriedad descrito en 7.4: si el seed contuviera al homónimo menor, la regla elegiría al famoso sin avisar. Por eso las filas resueltas así se listan en §2.4.

Conclusión: los pesos son una heurística, pero apenas condicionan el resultado. Lo que importa es combinar las tres señales, no el valor exacto de cada peso. Se mantienen los pesos actuales.

### 7.4 Limitaciones

1. **Una sola fuente.** Todo sale de Wikidata. Hereda sus sesgos de cobertura: los autores occidentales y canónicos están mejor descritos. Las 500 filas del seed son autores conocidos, así que la cobertura del 100 % no se extrapola a una lista de autores poco conocidos.
2. **La notoriedad como desempate.** La puntuación y la regla de dominancia favorecen al homónimo más famoso. Es lo correcto para este seed, pero fallaría si la lista incluyera a un autor menor con el mismo nombre que otro famoso. Sin contexto adicional (por ejemplo, un ISBN o un título de obra en el seed) no se puede distinguir.
3. **Pesos heurísticos no calibrados.** Los pesos y los umbrales no se calibraron contra un conjunto etiquetado. El análisis de sensibilidad (7.3) muestra que el resultado apenas depende de ellos en este seed, pero no garantiza lo mismo con otra lista. Cada decisión es trazable (`candidates`, `seed_resolution.note`).
4. **Búsqueda solo en inglés y español.** Todos los nombres del seed están en alfabeto latino. Para nombres en otras escrituras habría que añadir idiomas de búsqueda.
5. **Comparación de nombres sin diacríticos.** Al comparar se quitan las tildes, y eso hace iguales a «Nguyễn Du» y «Nguyễn Dữ», dos escritores vietnamitas distintos. Aquí no ha causado errores (la notoriedad los separa), pero en idiomas donde los diacríticos distinguen nombres convendría comparar con ellos.
6. **Instantánea.** Los datos reflejan Wikidata en la fecha de descarga (`retrieved_at`). Una ejecución online posterior puede dar resultados distintos; la caché permite reproducir exactamente esta versión.
7. **Selección de valores únicos.** Para lugares con varios valores sin rango preferente se elige el de menor QID. Es determinista pero arbitrario, y queda marcado en `conflicting_fields`.
8. **Lista de no-personas escrita a mano** (`Anonymous`, `Various Authors`…). Una lista nueva podría traer otros genéricos («Anónimo», «VV. AA.», «Unknown»). Los más comunes ya están incluidos.
9. **Seudónimos.** Cada fila del seed apunta a la persona real. El seudónimo se conserva como nombre (`author_names`, `kind='pseudonym'`), pero no como entidad propia. Si se necesitara atribuir obras al seudónimo, habría que modelarlo aparte.
10. **Etiquetas en inglés.** Nombres de lugares, ocupaciones e idiomas se guardan en inglés, con respaldo en `mul` y español. `label_es` sí se guarda para el nombre del autor.
