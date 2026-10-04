"""Escribe los objetos de la corrida en salida/<runId>/objetos/ y prepara markdown/."""

from __future__ import annotations

import json
from pathlib import Path

from indexador.estado import EstadoLote

ARCHIVOS_DE_OBJETOS = {
    "catalogFiles": "catalog_files.json",
    "learningElements": "learning_elements.json",
    "backings": "backings.json",
    "usages": "usages.json",
    "provenance": "provenance.json",
}


def escribir_salidas(estado: EstadoLote) -> dict:
    carpeta = Path(estado["carpetaSalida"])
    (carpeta / "objetos").mkdir(parents=True, exist_ok=True)
    (carpeta / "markdown").mkdir(parents=True, exist_ok=True)
    objetos = estado["objetos"]
    for campo, nombre in ARCHIVOS_DE_OBJETOS.items():
        filas = [o.model_dump(mode="json") for o in getattr(objetos, campo)]
        (carpeta / "objetos" / nombre).write_text(
            json.dumps(filas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return {}
