# Lote de ejemplo: curso dictado 412711

Curso real de Brightspace **Mediación de la Convivencia Escolar** (maestría), tomado del seed de
`mods/learning-catalog` (`seed/_data-catalog-core.js` y `seed/_data-platform-fixtures.js`).

## Qué es real y qué es sintético

| Parte | Origen |
| --- | --- |
| Curso dictado, curso y los tres RA (code, enunciado, bloomLevel) | Real, del seed del mod |
| Identificadores, títulos, módulos, orden, URLs y fechas de los 12 archivos | Real, de la extracción de Brightspace |
| Contenido de los `.md` | Sintético: la extracción no descargó ningún archivo |
| `contentHash` | Sintético: sha256 del `.md`, no del archivo original |
| Ids de la plataforma (`off-412711`, `ra-01`, ...) | Ficticios, el prototipo no tiene base de datos |

Todos los archivos están marcados con `sintetico: true` en `lote.json`.

## Casos de prueba que cubre

| Archivo | Caso | Resultado esperado |
| --- | --- | --- |
| 4542265 y sim-0001 | Mismo contenido en dos módulos | Un elemento con dos usos |
| 4542268 | Ya existe en `contexto/catalogo.json` | Se vincula al elemento conocido |
| 4542267 | HTML sin conversor en el core (`unsupported`) | Ilegible, con motivo |
| 4542281 | Archivo corrupto (`failed`) | Ilegible, con motivo |
| sim-0002 | PDF escaneado sin texto útil | Ilegible por el agente |
| 4542275 | Markdown truncado por el core | Se procesa con advertencia |

## Mantenimiento

Si se edita un `.md`, hay que recalcular los hashes:

```bash
python scripts/actualizar_hashes.py ejemplos/curso-412711
```

`contexto/catalogo.json` guarda el hash de `metodologia-del-curso.md`; si se edita ese archivo,
hay que actualizarlo a mano.

## Respuestas esperadas

`esperado.json` dice qué debería producir el agente con cada archivo: estado, nivel cognitivo,
tipo de conocimiento, autores, términos clave, rango de tiempo y, por cada RA, si el elemento lo
respalda y con qué carácter. Es un **borrador** pendiente de revisión del equipo: cuando se
revise, cambiar `estado` a `"revisado"`.

Se usa con `python -m indexador ... --evaluar` para medir el acuerdo por campo entre el agente
y estas respuestas.
