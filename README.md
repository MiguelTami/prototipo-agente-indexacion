# Prototipo del agente de indexación (Agente A)

Prototipo aislado del agente que procesa los documentos del LMS y genera los objetos de
Learning Catalog: `CatalogFile`, `LearningElement`, `Backing`, `Usage` y `Provenance`.

| Criterio de aceptación | Cómo lo cumple |
| --- | --- |
| Aislado: sin LMS, mod ni base de datos | No importa nada de `up1`; lee y escribe carpetas. Un test lo verifica |
| Entradas y salidas en archivos | `lote.json` + contexto + `.md` del core → objetos JSON, markdown y reporte |
| Metadata y objetos completos | Los 5 objetos del mod, con proveniencia por campo; tests contra una copia fijada del mod |
| Gatillable desde un único llamado | `indexar(entrada, salida)` o `python -m indexador` |

El plan completo vive en el documento "Agente A: plan del primer prototipo de indexación".

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"             # agente + pruebas
pip install -e ".[gemini]"          # opcional: Gemini (Google AI Studio)
pip install -e ".[pdf]"             # opcional: preparar lotes desde PDF reales
pip install -e ".[bedrock]"         # opcional: Amazon Bedrock
pip install -e ".[notebook]"        # opcional: JupyterLab para el notebook
```

## Uso

Un único llamado procesa un lote completo y crea `salida/<runId>/`:

```bash
python -m indexador --entrada ejemplos/curso-412711 --salida salida
```

o desde Python:

```python
from indexador import indexar

resultado = indexar("ejemplos/curso-412711", "salida")
print(resultado.reporte.totales)
```

El recorrido guiado está en `notebooks/prototipo.ipynb` (abrir con `jupyter lab`).

### Correr con PDF reales

`indexador.preparar` hace fuera de uP1 lo que en la plataforma hace el core: convierte cada PDF
a markdown (una sección `## Página N` por página), calcula el `contentHash` real sobre los bytes
del PDF y marca como `failed` un PDF dañado, protegido o sin texto. Arma un lote listo para el
agente.

```bash
# 1. Poner los PDF en lotes-reales/<curso>/pdfs/  (lotes-reales/ está en .gitignore)
# 2. Armar el lote
python -m indexador.preparar --pdfs lotes-reales/mi-curso/pdfs --salida lotes-reales/mi-curso --curso "Nombre del curso"
# 3. Correr el agente
python -m indexador --entrada lotes-reales/mi-curso --salida salida --config config.gemini.yaml --trazar
```

- Si el nombre del archivo dice "Semana N", ese es el módulo del uso; si no, su posición en la
  carpeta. Los archivos se ordenan de forma natural (Semana 2 antes que Semana 10).
- Sin `--ras`, el contexto no tiene resultados de aprendizaje: el agente genera elementos, usos y
  proveniencia, pero no respaldos. Con `--ras ras.json` sí los propone. El archivo es una lista de
  `{id, code, name, bloomLevel}`; `bloomLevel` es opcional, como en el modelo compartido:

  ```json
  [
    {"id": "ra-01", "code": "RA-01", "name": "El estudiante analiza ...", "bloomLevel": "Analyze"},
    {"id": "ra-02", "code": "RA-02", "name": "El estudiante identifica ..."}
  ]
  ```

  También se pueden escribir directamente en `resultadosAprendizaje` de `contexto/curso.json` de un
  lote ya preparado, sin volver a convertir los PDF.
- Con `--urls urls.json` se llena `sourceUrl` de cada archivo, que llega a `CatalogFile.sourceUrl`.
  Es donde vive el archivo original y lo que la plataforma abre para mostrarlo. El archivo es un
  objeto `{"nombre del PDF": "URL"}`; un PDF sin URL queda con `sourceUrl` vacío, y una URL que
  nombra un PDF que no está en la carpeta detiene la preparación:

  ```json
  {"Semana 01 - Introduccion.pdf": "https://drive.google.com/file/d/.../view"}
  ```
- No hay `esperado.json` para un lote real, así que `--evaluar` no aplica salvo que alguien lo
  escriba.

### Ver cada nodo y medir el resultado

```bash
python -m indexador --entrada ejemplos/curso-412711 --salida salida --trazar --evaluar
```

- `--trazar` imprime lo que devolvió cada nodo, contenido por contenido, y escribe `traza.json`
  y `traza.md` en la carpeta de la corrida.
- `--evaluar` compara la corrida con las respuestas esperadas (`esperado.json` de la carpeta de
  entrada, u otro archivo con `--esperado`) y escribe `evaluacion.json` y `evaluacion.md` con el
  acuerdo por campo y cada desacuerdo.

La evaluación también se puede correr sobre una corrida anterior:

```python
from indexador.evaluacion import evaluar, escribir_evaluacion

evaluacion = evaluar("salida/<runId>", "ejemplos/curso-412711/esperado.json")
escribir_evaluacion(evaluacion, "salida/<runId>")
```

Qué se mide, por elemento: nivel cognitivo, tipo de conocimiento, idioma, autores, términos
clave, rango de tiempo y que el título no copie el del LMS; por respaldo: si aporta al RA y con
qué carácter; por archivo: el estado final. Es la tasa de acuerdo humano-IA por campo que el
diseño del producto pide medir antes de lanzar.

### Qué escribe una corrida

```
salida/<runId>/
  objetos/catalog_files.json       un CatalogFile por archivo, Unreadable si no se pudo leer
  objetos/learning_elements.json   un elemento por contenido nuevo
  objetos/backings.json            respaldos propuestos (siempre Proposed)
  objetos/usages.json              un uso por archivo legible
  objetos/provenance.json          de dónde sale cada campo: AiAgent o Lms
  markdown/<elemento>.md           contenido extraído con su metadata, el que irá a S3
  reporte.json                     para máquinas
  reporte.md                       para personas: totales, ilegibles, razones de los respaldos
  traza.json, traza.md             con --trazar: lo que devolvió cada nodo
  evaluacion.json, evaluacion.md   con --evaluar: acuerdo con las respuestas esperadas
```

### Modo del modelo

`indexador/config.yaml` trae la configuración por defecto, en modo **simulado**: heurísticas
deterministas, sin red ni credenciales, útiles para probar el flujo pero no para juzgar la
calidad de la metadata.

**Gemini (Google AI Studio).** Copiar `.env.example` como `.env` y poner la llave en
`GOOGLE_API_KEY` (el `.env` nunca se sube: está en `.gitignore`). Revisar en
[AI Studio](https://aistudio.google.com/rate-limit) qué modelos tiene la capa gratuita y ajustar
`llm.modelo` en `config.gemini.yaml` si hace falta. Luego:

```bash
python -m indexador --entrada ejemplos/curso-412711 --salida salida --config config.gemini.yaml --trazar --evaluar
```

`config.gemini.yaml` procesa 2 contenidos a la vez y reintenta con espera creciente, porque la
capa gratuita limita las solicitudes por minuto. El lote de ejemplo hace 18 llamadas al modelo
(metadata y respaldos de 9 elementos).

**Amazon Bedrock.** Copiar `indexador/config.yaml`, cambiar `llm.modo` a `"bedrock"`, poner en
`llm.modelo` el id de un modelo que soporte tool use, tener credenciales de AWS y correr con
`--config mi-config.yaml`. Si el modelo falla tras los reintentos, el contenido sale como
ilegible con su motivo y la corrida sigue.

## Cómo funciona

```
Grafo del lote:
  cargar_lote → (un Send por contenido único) → procesar_contenido
              → consolidar_lote → escribir_salidas → generar_reporte

Subgrafo de un contenido:
  revisar_legibilidad → ¿legible?
    no → marcar_ilegible → armar_objetos
    sí → resolver_identidad → ¿ya está en el catálogo?
           sí → armar_objetos (solo CatalogFile y Usage)
           no → generar_metadata → ¿metadata válida?
                  no → marcar_ilegible → armar_objetos
                  sí → proponer_respaldos → armar_objetos
```

- Un **contenido** es un grupo de archivos con el mismo `contentHash`: se procesa una vez y
  genera un elemento con un uso por archivo.
- Un archivo **ilegible** nunca es un error: sale como `CatalogFile` en estado `Unreadable` y
  como una fila del reporte con su motivo.
- **Nada nace validado** y ningún campo de profesor o curador se llena.

## Pruebas

```bash
pytest
```

Corren en modo simulado, sin red. `tests/fixtures/objetos-mod/` guarda una copia fijada de los
objetos del mod: si el mod cambia, se reemplaza la copia y los tests dicen qué actualizar.

## Estructura

```
indexador/
  corrida.py          indexar(): el único punto de entrada
  grafo.py            grafo del lote y subgrafo por contenido (LangGraph)
  estado.py           estado de los dos grafos
  nodos/              un módulo por nodo
  legibilidad.py      reglas de legibilidad
  objetos.py          construcción de objetos y proveniencia
  llm.py              modelo simulado y Amazon Bedrock
  preparar.py         arma un lote desde una carpeta de PDF
  traza.py            traza nodo por nodo
  evaluacion.py       acuerdo con las respuestas esperadas
  prompts/            prompts del modelo real
  esquemas/           modelos Pydantic de entrada, salida y reporte
  config.yaml         configuración por defecto
ejemplos/             lotes de ejemplo (ver su README)
notebooks/            recorrido guiado
scripts/              utilidades para mantener los lotes
tests/
```

## Límites conocidos de esta versión

- Un archivo da un solo elemento, como dice el modelo del mod (`CatalogFile.learningElementId`
  es una sola referencia). Partir un archivo extenso en varios elementos es la decisión abierta
  A4 del diseño ("fragmento como unidad de recomendación").
- La identidad se resuelve solo por hash exacto; la similitud necesita embeddings.
- Solo respaldos del propio curso (sin `proposedWithoutUsage`).
- Video y audio solo si llegan ya transcritos en un `.md`.
- Los valores que pone una regla fija (por ejemplo `rights = Institution`) no tienen
  `Provenance`: el mod no tiene un origen para ellos.
- La razón de cada respaldo vive en el reporte, porque `Backing` no tiene un campo para ella.
