"""Nodo armar_objetos. Por ahora solo conserva lo que armaron los nodos anteriores
(el CatalogFile de un ilegible); los objetos de un contenido legible llegan en los pasos 6 y 7."""

from __future__ import annotations

from indexador.esquemas.salida import ObjetosCorrida
from indexador.estado import EstadoContenido


def armar_objetos(estado: EstadoContenido) -> dict:
    return {"pasos": ["armar_objetos"], "objetos": estado.get("objetos") or ObjetosCorrida()}
