# Prototipo del agente de indexación (Agente A)

Prototipo aislado del agente que procesa los documentos del LMS y genera los objetos de
Learning Catalog: LearningElement, Backing, Usage, CatalogFile y Provenance.

- **Aislado:** no se conecta al LMS, al mod `learning-catalog` ni a la base de datos.
- **Entradas y salidas en archivos:** lee una carpeta de lote y escribe una carpeta de salida.
- **Un único llamado:** `indexar(entrada, salida)`.

El plan completo vive en el documento "Agente A: plan del primer prototipo de indexación".

## Requisitos

- Python 3.10 o superior

## Instalación

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso

Un único llamado procesa un lote completo y crea `salida/<runId>/`:

```bash
python -m indexador --entrada ejemplos/curso-412711 --salida salida
```

o desde Python (por ejemplo, en un notebook):

```python
from indexador import indexar

resultado = indexar("ejemplos/curso-412711", "salida")
print(resultado.reporte.totales)
```

Cada corrida escribe:

```
salida/<runId>/
  objetos/catalog_files.json
  objetos/learning_elements.json
  objetos/backings.json
  objetos/usages.json
  objetos/provenance.json
  markdown/
  reporte.json
  reporte.md
```

La configuración por defecto está en `indexador/config.yaml` (modo del LLM, umbrales, versiones).
Se puede pasar otra con `--config`.

## Pruebas

```bash
pytest
```

## Estructura

```
indexador/
  corrida.py          indexar(): el único punto de entrada
  grafo.py            grafo del lote y subgrafo por contenido (LangGraph)
  estado.py           estado de los dos grafos
  nodos/              un módulo por nodo
  esquemas/           modelos Pydantic de entrada, salida y reporte
  config.yaml         configuración por defecto
ejemplos/             lotes de ejemplo
scripts/              utilidades para mantener los lotes
tests/
```
