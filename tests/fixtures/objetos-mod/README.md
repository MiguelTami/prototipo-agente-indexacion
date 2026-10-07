# Copia fijada de los objetos del mod

Copia exacta de las definiciones de objeto que el prototipo replica. Los tests de
`tests/test_fidelidad_mod.py` comparan los esquemas Pydantic contra estos archivos: si el mod
cambia, se reemplaza la copia y los tests muestran qué hay que actualizar en el prototipo.

| Archivo | Origen | Rama | Último commit del origen |
| --- | --- | --- | --- |
| `CatalogFile.json`, `LearningElement.json`, `Backing.json`, `Usage.json`, `Provenance.json` | `up1/mods/learning-catalog/objects/` | `integration/develop-candidate` | `a12289d` (2026-10-02) |
| `rt__LearningOutcome__curricularsection.json` | `up1/mods/curriculum-design/objects/RecordTypes/` | `develop` | `117d8ba` (2026-04-29) |

El prototipo no importa nada de `up1`: esta copia es la única relación con el mod, y es solo
para pruebas.
