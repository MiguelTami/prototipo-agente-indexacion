"""Agrupa los archivos del lote por contenido (contentHash), conservando el orden del manifiesto."""

from __future__ import annotations

from indexador.estado import Contenido, EstadoLote


def cargar_lote(estado: EstadoLote) -> dict:
    grupos: dict[str, Contenido] = {}
    for archivo in estado["entrada"].lote.archivos:
        clave = archivo.core.contentHash
        grupos.setdefault(clave, {"contentHash": clave, "archivos": []})["archivos"].append(archivo)
    return {"contenidos": list(grupos.values())}
