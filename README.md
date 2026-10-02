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

## Pruebas

```bash
pytest
```

## Estructura

```
indexador/            código del agente
  esquemas/           modelos Pydantic de entrada y salida
ejemplos/             lotes de ejemplo
scripts/              utilidades para mantener los lotes
tests/
```
