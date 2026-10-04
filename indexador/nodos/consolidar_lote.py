"""Junta los objetos de todos los contenidos en un solo conjunto para la corrida."""

from __future__ import annotations

from indexador.esquemas.salida import ObjetosCorrida
from indexador.estado import EstadoLote


def consolidar_lote(estado: EstadoLote) -> dict:
    total = ObjetosCorrida()
    for resultado in estado.get("resultados", []):
        parcial = resultado["objetos"]
        total.catalogFiles += parcial.catalogFiles
        total.learningElements += parcial.learningElements
        total.backings += parcial.backings
        total.usages += parcial.usages
        total.provenance += parcial.provenance
    return {"objetos": total}
