"""Nodo resolver_identidad: ¿este contenido ya es un elemento del catálogo?

El elemento se identifica por contenido, no por ubicación. Dentro del lote, los archivos con el
mismo contentHash ya llegan agrupados en un solo contenido (cargar_lote). Aquí se compara contra
los elementos que ya existen en contexto/catalogo.json:

- Hash exacto conocido: se vincula al elemento existente, sin regenerar su metadata (no se
  sobrescribe lo que pudo validar una persona) ni sus respaldos.
- Sin coincidencia: es un elemento nuevo con id derivado del hash.

La similitud de texto o semántica (identificationMethod = ContentSimilarity) queda fuera de esta
versión: necesita embeddings.
"""

from __future__ import annotations

from indexador.estado import EstadoContenido
from indexador.objetos import id_learning_element


def resolver_identidad(estado: EstadoContenido) -> dict:
    content_hash = estado["contenido"]["contentHash"]
    conocidos = {e.contentHash: e for e in estado["entrada"].catalogo.elementos}
    existente = conocidos.get(content_hash)
    if existente:
        return {
            "pasos": ["resolver_identidad"],
            "learningElementId": existente.learningElementId,
            "elementoExistente": True,
            "advertencias": [
                f"Vinculado al elemento existente {existente.learningElementId} "
                f"(«{existente.descriptiveTitle}») por hash exacto: no se regenera su metadata."
            ],
        }
    return {
        "pasos": ["resolver_identidad"],
        "learningElementId": id_learning_element(content_hash),
        "elementoExistente": False,
    }
