"""Nodo armar_objetos. Esqueleto del paso 2: todavía no arma ningún objeto."""

from __future__ import annotations

from indexador.esquemas.salida import ObjetosCorrida
from indexador.estado import EstadoContenido


def armar_objetos(estado: EstadoContenido) -> dict:
    return {"pasos": ["armar_objetos"], "objetos": ObjetosCorrida()}
