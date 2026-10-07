"""Construcción de los objetos de salida. Sin LangGraph: cada función se prueba sola.

Reglas del producto que se aplican aquí:
- Nada nace validado: todo Backing sale en Proposed y ningún campo de profesor o curador se llena.
- Proveniencia por campo: cada campo que llena el agente (AiAgent) o que viene del LMS (Lms)
  tiene su Provenance. Los valores que pone una regla fija del producto (rights=Institution,
  validityStatus=Valid, usageCharacter=Complementary, ...) no la tienen: el mod no tiene un
  origen para ellos (hueco abierto en el plan).
"""

from __future__ import annotations

from typing import Iterable, Optional

from indexador.config import Config
from indexador.esquemas.entrada import ArchivoEntrada, ContextoCurso
from indexador.esquemas.salida import (
    Backing,
    CatalogFile,
    ElementType,
    EntityType,
    LearningElement,
    Origin,
    Provenance,
    Usage,
)
from indexador.llm import JuicioRespaldo, MetadataPropuesta

# Formato del archivo en el LMS → tipo del elemento.
TIPO_POR_FORMATO: dict[str, ElementType] = {
    "Pdf": "Document",
    "Word": "Document",
    "Video": "Video",
    "Audio": "Audio",
    "Exam": "Exam",
    "Other": "Document",
}

CAMPOS_LMS_CATALOG_FILE = ("sourceIdentifier", "fileType", "sourceUrl", "sourceVersion", "offeringId", "contentHash")
CAMPOS_AGENTE_CATALOG_FILE = ("learningElementId", "identificationMethod", "detectionExtractionStatus")
CAMPOS_AGENTE_ELEMENTO = (
    "descriptiveTitle",
    "description",
    "identifiedAuthors",
    "keywords",
    "knowledgeType",
    "language",
    "estimatedTime",
    "cognitiveLevel",
)
CAMPOS_LMS_USAGE = ("offeringId", "weekOrUnit", "order")
# Lo único que se sabe de un contenido sin haberlo leído: viene del LMS.
CAMPOS_LMS_ELEMENTO_SIN_DESCRIBIR = ("descriptiveTitle", "type")
# Idioma de un contenido que no se pudo leer, cuando el curso tampoco lo declara. El elemento sale
# con metadataStatus en false, así que el Curador lo revisa de todas formas.
IDIOMA_POR_DEFECTO = "es"
CAMPOS_AGENTE_BACKING = ("learningOutcomeId", "character", "offeredCognitiveLevel", "modelConfidence")


def id_learning_element(content_hash: str) -> str:
    """Id local de un elemento nuevo: estable, derivado del contenido."""
    return f"le-{content_hash[:12]}"


def id_catalog_file(archivo: ArchivoEntrada) -> str:
    return f"cf-{archivo.sourceIdentifier}"


def id_usage(archivo: ArchivoEntrada) -> str:
    return f"us-{archivo.sourceIdentifier}"


def id_backing(learning_element_id: str, codigo_ra: str) -> str:
    return f"bk-{learning_element_id}-{codigo_ra}"


# --- CatalogFile ----------------------------------------------------------------------------


def catalog_file_ilegible(
    archivo: ArchivoEntrada, learning_element_id: str, offering_id: str, ahora: str
) -> CatalogFile:
    """CatalogFile de un archivo que no se pudo leer, ya identificado por hash exacto.

    Que no se pueda leer no impide identificarlo: el contentHash lo calcula el core sobre los bytes
    del archivo, antes del agente. Así el archivo apunta siempre a un elemento, como exige el mod
    (CatalogFile.learningElementId es obligatorio), y la tarea UnreadableFile llega sobre un archivo
    que ya pertenece a un contenido (LAB-40).
    """
    return CatalogFile(
        id=id_catalog_file(archivo),
        sourceSystem="Lms",
        sourceIdentifier=archivo.sourceIdentifier,
        fileType=archivo.fileType,
        sourceUrl=archivo.sourceUrl,
        offeringId=offering_id,
        learningElementId=learning_element_id,
        contentHash=archivo.core.contentHash,
        identificationMethod="ExactHash",
        identificationPending=False,
        detectionExtractionStatus="Unreadable",
        sourceVersion=archivo.sourceVersion,
        detectedAt=ahora,
    )


def catalog_file_extraido(
    archivo: ArchivoEntrada, learning_element_id: str, offering_id: str, ahora: str
) -> CatalogFile:
    """CatalogFile de un archivo leído, identificado por hash exacto."""
    return CatalogFile(
        id=id_catalog_file(archivo),
        sourceSystem="Lms",
        sourceIdentifier=archivo.sourceIdentifier,
        fileType=archivo.fileType,
        sourceUrl=archivo.sourceUrl,
        offeringId=offering_id,
        learningElementId=learning_element_id,
        contentHash=archivo.core.contentHash,
        identificationMethod="ExactHash",
        identificationPending=False,
        detectionExtractionStatus="Extracted",
        sourceVersion=archivo.sourceVersion,
        detectedAt=ahora,
    )


# --- LearningElement ------------------------------------------------------------------------


def metadata_completa(elemento: LearningElement) -> bool:
    """Campos de metadata del contrato de salida (CLAUDE.md, sección 3.9) presentes."""
    return all(
        [
            elemento.descriptiveTitle.strip(),
            (elemento.description or "").strip(),
            elemento.keywords,
            elemento.cognitiveLevel,
            elemento.type,
            elemento.estimatedTime > 0,
            elemento.language.strip(),
            elemento.rights,
        ]
    )


def elemento_sin_describir(
    learning_element_id: str, archivo: ArchivoEntrada, contexto: ContextoCurso
) -> LearningElement:
    """LearningElement mínimo de un contenido que no se pudo leer (LAB-40).

    Es el patrón que el mod ya usa en sus datos de ejemplo (seed/_data-catalog-core.js y
    seed/_data-metrics-demo.js): el contenido existe, sin describir, y su archivo ilegible se le
    cuelga. Lleva solo lo que se sabe sin leerlo: el título con que aparece en el LMS y el tipo
    según el formato, los dos con Provenance de origen Lms, y el idioma del curso. Queda en
    Detected y con metadataStatus en false: incompleto frente al contrato de salida, que es lo que
    es. El título del LMS no es un descriptiveTitle generado: lo dice su Provenance, y el Curador
    lo reemplaza al resolver la tarea del archivo.
    """
    return LearningElement(
        id=learning_element_id,
        descriptiveTitle=archivo.tituloLms,
        type=TIPO_POR_FORMATO[archivo.fileType],
        language=contexto.curso.language or IDIOMA_POR_DEFECTO,
        estimatedTime=0,
        ingestionStatus="Detected",
        metadataStatus=False,
    )


def learning_element(
    learning_element_id: str,
    metadata: MetadataPropuesta,
    archivo: ArchivoEntrada,
    extracted_text_url: str,
) -> LearningElement:
    elemento = LearningElement(
        id=learning_element_id,
        descriptiveTitle=metadata.descriptiveTitle,
        description=metadata.description,
        identifiedAuthors=metadata.identifiedAuthors,
        keywords=metadata.keywords,
        type=TIPO_POR_FORMATO[archivo.fileType],
        knowledgeType=metadata.knowledgeType,
        language=metadata.language,
        estimatedTime=metadata.estimatedTime,
        cognitiveLevel=metadata.cognitiveLevel,
        extractedTextUrl=extracted_text_url,
        metadataStatus=False,
    )
    elemento.metadataStatus = metadata_completa(elemento)
    return elemento


# --- Usage y Backing ------------------------------------------------------------------------


def usage(archivo: ArchivoEntrada, learning_element_id: str, offering_id: str) -> Usage:
    """El elemento en el curso dictado, con semana y orden precargados desde el LMS."""
    return Usage(
        id=id_usage(archivo),
        learningElementId=learning_element_id,
        offeringId=offering_id,
        weekOrUnit=archivo.modulo,
        order=archivo.orden,
    )


def backings(
    juicios: Iterable[JuicioRespaldo], learning_element_id: str, contexto: ContextoCurso
) -> list[Backing]:
    """Un Backing propuesto por cada RA al que el modelo dijo que el elemento aporta."""
    ras = {ra.code: ra for ra in contexto.resultadosAprendizaje}
    return [
        Backing(
            id=id_backing(learning_element_id, juicio.codigoRA),
            learningElementId=learning_element_id,
            courseId=contexto.curso.id,
            learningOutcomeId=ras[juicio.codigoRA].id,
            character=juicio.caracter or "Develops",
            offeredCognitiveLevel=juicio.nivelOfrecido,
            modelConfidence=juicio.confianza,
            status="Proposed",
            proposedWithoutUsage=False,
        )
        for juicio in juicios
        if juicio.aporta and juicio.codigoRA in ras
    ]


# --- Provenance -----------------------------------------------------------------------------


def provenance(
    objeto,
    entity_type: EntityType,
    campos: Iterable[str],
    origin: Origin,
    ahora: str,
    config: Config,
    modelo: Optional[str] = None,
) -> list[Provenance]:
    """Un Provenance por cada campo con valor. Los de AiAgent llevan agente, modelo y configuración."""
    es_agente = origin == "AiAgent"
    identificador = f"{config.agentVersion} · {modelo}" if es_agente and modelo else (
        config.agentVersion if es_agente else None
    )
    filas = []
    for campo in campos:
        valor = getattr(objeto, campo)
        if valor is None or valor == []:
            continue
        filas.append(
            Provenance(
                id=f"pv-{objeto.id}-{campo}",
                entityType=entity_type,
                entityId=objeto.id,
                fieldName=campo,
                origin=origin,
                agentIdentifier=identificador,
                recordedAt=ahora,
                configVersion=config.configVersion if es_agente else None,
            )
        )
    return filas


def provenance_catalog_file(archivo: CatalogFile, ahora: str, config: Config, modelo: Optional[str] = None):
    return provenance(archivo, "CatalogFile", CAMPOS_LMS_CATALOG_FILE, "Lms", ahora, config) + provenance(
        archivo, "CatalogFile", CAMPOS_AGENTE_CATALOG_FILE, "AiAgent", ahora, config, modelo
    )
