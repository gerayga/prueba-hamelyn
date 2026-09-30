# 03: Ajustes de reglas y enriquecimiento

## Qué decidí sobre la resolución
1. **Aceptar Q21070568 («humano cuya existencia se discute») como persona.** Prefiero una regla general a un override para Homero.
2. **Regla de dominancia.** Si el mejor candidato tiene al menos 5 veces los sitelinks del segundo, no se exige margen de score. Resuelve los 13 casos sin 13 excepciones manuales.
3. **Override de Mary Beard → Q458403 (la clasicista).** Es el único caso realmente ambiguo: la alternativa, Mary Ritter Beard, tiene una notoriedad parecida. Lo decidí por el contexto del seed.

Validación: el diff de la resolución antes y después mostró que solo cambiaron los 14 casos previstos, y el único QID distinto fue el de Homero.

## Qué pedí sobre el enriquecimiento
Descargar los atributos de cada autor, guardar los valores con varias opciones en tablas de relación y exportar a CSV.

## Problemas que aparecieron y cómo se resolvieron
- **Fechas.** El endpoint SPARQL desplaza un año las fechas a.C. y convierte las julianas a gregoriano. La IA lo detectó con una prueba antes de dar el dato por bueno y propuso leer las fechas del JSON original, guardándolas con su precisión y su calendario en lugar de normalizarlas. Lo aprobé.
- **Varios valores por campo.** Safo tiene 9 fechas de nacimiento. Se sigue el criterio de Wikidata (el valor de mejor rango); lo que sigue en conflicto se marca en `conflicting_fields`. Los IDs externos (VIAF, ISNI) pueden tener varios valores legítimamente y se guardan todos.
- **Etiquetas `mul`.** Rowling, Hugo, Kipling y Almudena Grandes no tenían etiqueta en inglés. Se añadió `mul` como respaldo.
- **Rate limiting.** Se reforzaron los reintentos y se quitó el parámetro `maxlag`, que está pensado para bots que editan.
- **Determinismo.** `retrieved_at` pasó a ser la fecha de descarga, no la de ejecución. Comprobado: dos ejecuciones offline dan CSV idénticos.
