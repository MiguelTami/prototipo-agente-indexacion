"""Nodo armar_objetos: convierte lo que decidieron los nodos anteriores en objetos del mod.

- Ilegible: conserva lo que armó marcar_ilegible (CatalogFile Unreadable ya asociado a su
  elemento, su Usage y, si el elemento es nuevo, el elemento sin describir).
- Vinculado a un elemento existente: un CatalogFile por archivo y un Usage en el curso dictado,
  sin tocar el elemento.
- Elemento nuevo: el LearningElement, un CatalogFile por archivo y un Usage en el curso dictado
  (el mod admite uno por elemento y curso dictado: el del primer archivo, ver
  objetos.archivo_del_uso), los Backing propuestos y el markdown que irá a S3.
Todo campo que llena el agente o que viene del LMS lleva su Provenance.
"""

from __future__ import annotations

import yaml

from indexador.esquemas.salida import ObjetosCorrida
from indexador.estado import EstadoContenido
from indexador.objetos import (
    CAMPOS_AGENTE_BACKING,
    CAMPOS_AGENTE_ELEMENTO,
    CAMPOS_LMS_USAGE,
    archivo_del_uso,
    backings,
    catalog_file_extraido,
    learning_element,
    provenance,
    provenance_catalog_file,
    usage,
)


def markdown_de_elemento(elemento, estado: EstadoContenido) -> str:
    """El markdown extraído con su metadata en front matter: lo que el core subirá a S3."""
    cabecera = {
        "learningElementId": elemento.id,
        "descriptiveTitle": elemento.descriptiveTitle,
        "description": elemento.description,
        "identifiedAuthors": elemento.identifiedAuthors,
        "keywords": elemento.keywords,
        "type": elemento.type,
        "knowledgeType": elemento.knowledgeType,
        "language": elemento.language,
        "estimatedTime": elemento.estimatedTime,
        "cognitiveLevel": elemento.cognitiveLevel,
        "contentHash": estado["contenido"]["contentHash"],
        "sourceIdentifiers": [a.sourceIdentifier for a in estado["contenido"]["archivos"]],
        "generadoPor": estado["config"].agentVersion,
        "modelo": estado.get("modelo"),
        "configVersion": estado["config"].configVersion,
        "generadoEn": estado["ahora"],
    }
    front = yaml.safe_dump(cabecera, allow_unicode=True, sort_keys=False)
    return f"---\n{front}---\n\n{estado['markdown']}"


def armar_objetos(estado: EstadoContenido) -> dict:
    if not estado.get("legible", True):
        return {"pasos": ["armar_objetos"], "objetos": estado.get("objetos") or ObjetosCorrida()}

    config, ahora = estado["config"], estado["ahora"]
    modelo = estado.get("modelo")
    entrada = estado["entrada"]
    offering_id = entrada.lote.offeringId
    le_id = estado["learningElementId"]
    archivos_lms = estado["contenido"]["archivos"]
    objetos = ObjetosCorrida()

    for archivo in archivos_lms:
        cf = catalog_file_extraido(archivo, le_id, offering_id, ahora)
        objetos.catalogFiles.append(cf)
        objetos.provenance += provenance_catalog_file(cf, ahora, config, modelo)
    uso = usage(archivo_del_uso(archivos_lms), le_id, offering_id)
    objetos.usages.append(uso)
    objetos.provenance += provenance(uso, "Usage", CAMPOS_LMS_USAGE, "Lms", ahora, config)

    salida = {"pasos": ["armar_objetos"], "objetos": objetos}
    if estado.get("elementoExistente"):
        return salida

    elemento = learning_element(le_id, estado["metadata"], archivos_lms[0], f"markdown/{le_id}.md")
    objetos.learningElements.append(elemento)
    objetos.provenance += provenance(
        elemento, "LearningElement", CAMPOS_AGENTE_ELEMENTO, "AiAgent", ahora, config, modelo
    )
    objetos.provenance += provenance(elemento, "LearningElement", ("type",), "Lms", ahora, config)

    for backing in backings(estado.get("juicios", []), le_id, entrada.contexto):
        objetos.backings.append(backing)
        objetos.provenance += provenance(
            backing, "Backing", CAMPOS_AGENTE_BACKING, "AiAgent", ahora, config, modelo
        )

    if not elemento.metadataStatus:
        salida["advertencias"] = ["La metadata del elemento quedó incompleta frente al contrato de salida."]
    salida["markdownElemento"] = markdown_de_elemento(elemento, estado)
    return salida
