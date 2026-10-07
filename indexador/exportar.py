"""Exporta una corrida a un solo JSON que un seed de uP1 puede cargar.

La corrida usa ids locales (le-..., cf-..., bk-...) y los ids de contexto del lote (act-..., off-...,
ra-...). Ninguno existe en una base de uP1, así que la exportación:
- deja los ids locales como `ref`, para que el seed una los objetos entre sí;
- quita `courseId` y `offeringId`, que el seed pone con los ids reales del curso que crea;
- cambia `learningOutcomeId` por el código del RA (`learningOutcomeCode`), que es la llave natural;
- deja `extractedTextUrl` vacío, porque en la corrida es una ruta local y no una URL;
- cuando un archivo, uso o respaldo apunta a un elemento que ya estaba en el catálogo (no creado
  en esta corrida), lo nombra por el `contentHash` con que el catálogo lo conoce
  (`existingElementContentHash`), porque su id local no existe en uP1.
Fuera de eso, los valores son los que produjo el agente, sin cambios.

Uso:
    python -m indexador.exportar --corrida salida/<runId> --entrada lotes-reales/mi-curso
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from indexador.esquemas.entrada import cargar_entrada

FORMATO = "indexador-catalogo/exportacion@1"
ARCHIVOS = {
    "learningElements": "learning_elements.json",
    "catalogFiles": "catalog_files.json",
    "usages": "usages.json",
    "backings": "backings.json",
    "provenance": "provenance.json",
}


class ErrorExportacion(Exception):
    """La corrida no se puede exportar tal como está."""


def _leer(carpeta: Path, nombre: str) -> list[dict]:
    ruta = carpeta / "objetos" / nombre
    if not ruta.is_file():
        raise ErrorExportacion(f"Falta {ruta}: ¿es la carpeta de una corrida?")
    return json.loads(ruta.read_text(encoding="utf-8"))


def _sin(fila: dict, *campos: str) -> dict:
    return {k: v for k, v in fila.items() if k not in campos}


def exportar(corrida: str | Path, entrada: str | Path) -> dict:
    """Arma la exportación de una corrida, con el contexto del lote del que salió."""
    corrida = Path(corrida)
    reporte = json.loads((corrida / "reporte.json").read_text(encoding="utf-8"))
    lote = cargar_entrada(entrada)
    if lote.lote.offeringId != reporte["offeringId"]:
        raise ErrorExportacion(
            f"La corrida es del curso dictado {reporte['offeringId']} y el lote de {lote.lote.offeringId}"
        )
    objetos = {clave: _leer(corrida, nombre) for clave, nombre in ARCHIVOS.items()}
    ras = {ra.id: ra.code for ra in lote.contexto.resultadosAprendizaje}

    existentes = {e.learningElementId: e.contentHash for e in lote.catalogo.elementos}
    elementos = [dict(_sin(e, "id", "extractedTextUrl"), ref=e["id"], extractedTextUrl=None) for e in objetos["learningElements"]]
    refs = {e["ref"] for e in elementos}

    def ref_elemento(fila: dict) -> dict:
        ref = fila.get("learningElementId")
        if ref is None or ref in refs:
            return {"learningElementRef": ref, "existingElementContentHash": None}
        if ref in existentes:
            return {"learningElementRef": None, "existingElementContentHash": existentes[ref]}
        raise ErrorExportacion(f"{fila['id']} apunta a {ref}, que no está ni en la corrida ni en el catálogo del lote")

    archivos = [
        dict(_sin(c, "id", "learningElementId", "offeringId"), ref=c["id"], **ref_elemento(c))
        for c in objetos["catalogFiles"]
    ]
    usos = [
        dict(_sin(u, "id", "learningElementId", "offeringId"), ref=u["id"], **ref_elemento(u))
        for u in objetos["usages"]
    ]
    respaldos = []
    for b in objetos["backings"]:
        if b["learningOutcomeId"] not in ras:
            raise ErrorExportacion(f"{b['id']} apunta al RA {b['learningOutcomeId']}, que no está en el lote")
        respaldos.append(
            dict(
                _sin(b, "id", "learningElementId", "learningOutcomeId", "courseId"),
                ref=b["id"],
                **ref_elemento(b),
                learningOutcomeCode=ras[b["learningOutcomeId"]],
            )
        )
    todas = refs | {a["ref"] for a in archivos} | {u["ref"] for u in usos} | {r["ref"] for r in respaldos}
    proveniencia = []
    for p in objetos["provenance"]:
        if p["entityId"] not in todas:
            raise ErrorExportacion(f"{p['id']} apunta a {p['entityId']}, que no está en la corrida")
        proveniencia.append(dict(_sin(p, "id", "entityId"), ref=p["id"], entityRef=p["entityId"]))

    contexto = lote.contexto
    return {
        "formato": FORMATO,
        "corrida": {
            "runId": reporte["runId"],
            "agentVersion": reporte["agentVersion"],
            "configVersion": reporte["configVersion"],
            "modeloLlm": reporte["modeloLlm"],
            "inicio": reporte["inicio"],
        },
        "curso": _sin(contexto.curso.model_dump(), "id"),
        "cursoDictado": _sin(contexto.cursoDictado.model_dump(), "id"),
        "resultadosAprendizaje": [_sin(ra.model_dump(), "id") for ra in contexto.resultadosAprendizaje],
        "learningElements": elementos,
        "catalogFiles": archivos,
        "usages": usos,
        "backings": respaldos,
        "provenance": proveniencia,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="indexador.exportar", description="Exporta una corrida para un seed de uP1")
    parser.add_argument("--corrida", required=True, help="Carpeta de la corrida (salida/<runId>)")
    parser.add_argument("--entrada", required=True, help="Carpeta del lote del que salió la corrida")
    parser.add_argument("--salida", default=None, help="Archivo JSON (por defecto, exportacion.json en la corrida)")
    args = parser.parse_args(argv)

    try:
        datos = exportar(args.corrida, args.entrada)
    except ErrorExportacion as error:
        print(f"No se pudo exportar: {error}", file=sys.stderr)
        return 1
    destino = Path(args.salida) if args.salida else Path(args.corrida) / "exportacion.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Exportación lista en {destino}")
    for clave in ARCHIVOS:
        print(f"  {clave:17} {len(datos[clave])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
