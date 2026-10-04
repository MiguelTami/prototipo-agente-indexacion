"""Construcción de objetos de salida a partir de la entrada. Sin LangGraph: se prueba sola."""

from __future__ import annotations

from indexador.esquemas.entrada import ArchivoEntrada
from indexador.esquemas.salida import CatalogFile


def id_catalog_file(archivo: ArchivoEntrada) -> str:
    return f"cf-{archivo.sourceIdentifier}"


def catalog_file_ilegible(archivo: ArchivoEntrada, offering_id: str, ahora: str) -> CatalogFile:
    """CatalogFile de un archivo que no se pudo leer: sin elemento ni identidad resuelta."""
    return CatalogFile(
        id=id_catalog_file(archivo),
        sourceSystem="Lms",
        sourceIdentifier=archivo.sourceIdentifier,
        fileType=archivo.fileType,
        sourceUrl=archivo.sourceUrl,
        offeringId=offering_id,
        contentHash=archivo.core.contentHash,
        detectionExtractionStatus="Unreadable",
        sourceVersion=archivo.sourceVersion,
        detectedAt=ahora,
    )
