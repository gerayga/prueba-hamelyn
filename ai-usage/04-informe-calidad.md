# 04: Informe de calidad

## Enfoque (propuesto por la IA en el plan y aprobado por mí)
- Un informe de calidad generado desde los datos, para que las cifras no se desactualicen.
- El análisis manual en un fichero aparte (`docs/quality_notes.md`), para que regenerar el informe no lo pise.
- Una muestra aleatoria con semilla fija, para verificarla a mano.
- Un test que ejecute el pipeline completo y compruebe que reproduce exactamente los exports del repo.

## Verificación de la muestra (20 filas)
La hizo la IA con conocimiento general, no contra una fuente externa (así se declara en §7.1 del informe). Yo revisé el resultado y los cambios propuestos.

- **Autores:** los 20 son la persona correcta.
- **Fechas de nacimiento:** 19 de 20 correctas. La que fallaba era la de **Ismat Chughtai**: Wikidata tiene 5 fechas de nacimiento y el desempate por orden del API elegía 1911, cuando lo correcto es 1915. La IA propuso cambiar el criterio a «gana la fecha con más referencias», sin contar las que solo indican que el dato se importó de Wikipedia, y lo acepté. En toda la base, solo cambiaron Chughtai y la fecha de muerte de Sadegh Hedayat, que también quedó corregida.
- **Murasaki Shikibu:** aparece en la comprobación «vida > 105 años», pero su fecha de muerte tiene precisión de siglo. No es un error, así que se documenta en lugar de corregirse.
