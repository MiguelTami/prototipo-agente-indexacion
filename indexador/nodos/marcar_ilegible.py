"""Nodo marcar_ilegible: un CatalogFile en estado Unreadable por cada archivo del contenido.

"Ilegible" es un estado de primera clase y una métrica visible, no un error escondido: el archivo
queda en la salida y en el reporte con su motivo, y la corrida sigue.
"""

from __future__ import annotations

from indexador.esquemas.salida import ObjetosCorrida
from indexador.estado import EstadoContenido
from indexador.objetos import catalog_file_ilegible, provenance_catalog_file


def marcar_ilegible(estado: EstadoContenido) -> dict:
    offering_id = estado["entrada"].lote.offeringId
    archivos = [
        catalog_file_ilegible(archivo, offering_id, estado["ahora"])
        for archivo in estado["contenido"]["archivos"]
    ]
    filas = [
        p
        for archivo in archivos
        for p in provenance_catalog_file(archivo, estado["ahora"], estado["config"])
    ]
    return {"pasos": ["marcar_ilegible"], "objetos": ObjetosCorrida(catalogFiles=archivos, provenance=filas)}
