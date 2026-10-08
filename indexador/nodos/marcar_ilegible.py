"""Nodo marcar_ilegible: los objetos de un contenido que no se pudo leer.

"Ilegible" es un estado de primera clase y una métrica visible, no un error escondido: el archivo
queda en la salida y en el reporte con su motivo, y la corrida sigue.

Desde LAB-40 el contenido llega ya identificado (resolver_identidad corre antes), así que cada
archivo sale como CatalogFile Unreadable asociado a su elemento, y el contenido tiene su Usage en
el curso dictado (uno por contenido, el del primer archivo), que es dato del LMS y no depende de
haber leído nada. Si el elemento no existía, nace uno sin
describir (objetos.elemento_sin_describir). Si ya existía, se vincula sin tocarlo, igual que un
archivo legible.
"""

from __future__ import annotations

from indexador.esquemas.salida import ObjetosCorrida
from indexador.estado import EstadoContenido
from indexador.objetos import (
    CAMPOS_LMS_ELEMENTO_SIN_DESCRIBIR,
    CAMPOS_LMS_USAGE,
    archivo_del_uso,
    catalog_file_ilegible,
    elemento_sin_describir,
    provenance,
    provenance_catalog_file,
    usage,
)


def marcar_ilegible(estado: EstadoContenido) -> dict:
    config, ahora = estado["config"], estado["ahora"]
    entrada = estado["entrada"]
    offering_id = entrada.lote.offeringId
    le_id = estado["learningElementId"]
    archivos_lms = estado["contenido"]["archivos"]
    objetos = ObjetosCorrida()

    for archivo in archivos_lms:
        cf = catalog_file_ilegible(archivo, le_id, offering_id, ahora)
        objetos.catalogFiles.append(cf)
        objetos.provenance += provenance_catalog_file(cf, ahora, config)
    uso = usage(archivo_del_uso(archivos_lms), le_id, offering_id)
    objetos.usages.append(uso)
    objetos.provenance += provenance(uso, "Usage", CAMPOS_LMS_USAGE, "Lms", ahora, config)

    if not estado.get("elementoExistente"):
        elemento = elemento_sin_describir(le_id, archivos_lms[0], entrada.contexto)
        objetos.learningElements.append(elemento)
        objetos.provenance += provenance(
            elemento, "LearningElement", CAMPOS_LMS_ELEMENTO_SIN_DESCRIBIR, "Lms", ahora, config
        )

    return {"pasos": ["marcar_ilegible"], "objetos": objetos}
