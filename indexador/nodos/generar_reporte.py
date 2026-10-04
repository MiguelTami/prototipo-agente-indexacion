"""Arma el reporte de la corrida y lo escribe en JSON (máquinas) y en markdown (personas)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from indexador.esquemas.reporte import Reporte, ReporteArchivo, Totales
from indexador.estado import EstadoLote, ResultadoContenido


def _estado_archivo(resultado: ResultadoContenido) -> str:
    if not resultado["legible"]:
        return "ilegible"
    if "armar_objetos" in resultado["pasos"] and resultado["objetos"].learningElements:
        return "procesado"
    return "sin_procesar"


def _ids_por_archivo(resultado: ResultadoContenido, source_identifier: str) -> dict[str, list[str]]:
    objetos = resultado["objetos"]
    archivo = [c.id for c in objetos.catalogFiles if c.sourceIdentifier == source_identifier]
    ids: dict[str, list[str]] = {
        "catalogFiles": archivo,
        "learningElements": [e.id for e in objetos.learningElements],
        "backings": [b.id for b in objetos.backings],
        "usages": [u.id for u in objetos.usages],
    }
    return {tipo: lista for tipo, lista in ids.items() if lista}


def construir_reporte(estado: EstadoLote) -> Reporte:
    entrada, config, objetos = estado["entrada"], estado["config"], estado["objetos"]
    filas: list[ReporteArchivo] = []
    for resultado in estado.get("resultados", []):
        for archivo in resultado["contenido"]["archivos"]:
            filas.append(
                ReporteArchivo(
                    sourceIdentifier=archivo.sourceIdentifier,
                    tituloLms=archivo.tituloLms,
                    contentHash=archivo.core.contentHash,
                    estado=_estado_archivo(resultado),
                    motivo=resultado["motivo"],
                    advertencias=resultado["advertencias"],
                    pasos=resultado["pasos"],
                    objetos=_ids_por_archivo(resultado, archivo.sourceIdentifier),
                )
            )
    orden = {a.sourceIdentifier: i for i, a in enumerate(entrada.lote.archivos)}
    filas.sort(key=lambda f: orden[f.sourceIdentifier])
    totales = Totales(
        archivosRecibidos=len(entrada.lote.archivos),
        contenidosUnicos=len(estado.get("contenidos", [])),
        archivosProcesados=sum(f.estado == "procesado" for f in filas),
        archivosIlegibles=sum(f.estado == "ilegible" for f in filas),
        catalogFiles=len(objetos.catalogFiles),
        learningElements=len(objetos.learningElements),
        backings=len(objetos.backings),
        usages=len(objetos.usages),
        provenance=len(objetos.provenance),
    )
    return Reporte(
        runId=estado["runId"],
        inicio=estado["inicio"],
        fin=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        agentVersion=config.agentVersion,
        configVersion=config.configVersion,
        modoLlm=config.llm.modo,
        modeloLlm=config.llm.modelo,
        lote=entrada.lote.descripcion,
        offeringId=entrada.lote.offeringId,
        totales=totales,
        archivos=filas,
    )


def reporte_markdown(reporte: Reporte) -> str:
    t = reporte.totales
    lineas = [
        f"# Reporte de indexación {reporte.runId}",
        "",
        f"- **Curso dictado:** {reporte.offeringId}",
        f"- **Inicio / fin:** {reporte.inicio} / {reporte.fin}",
        f"- **Agente:** {reporte.agentVersion} · configuración {reporte.configVersion}",
        f"- **LLM:** {reporte.modoLlm}" + (f" ({reporte.modeloLlm})" if reporte.modeloLlm else ""),
        "",
        "## Totales",
        "",
        "| Medida | Valor |",
        "| --- | --- |",
        f"| Archivos recibidos | {t.archivosRecibidos} |",
        f"| Contenidos únicos | {t.contenidosUnicos} |",
        f"| Archivos procesados | {t.archivosProcesados} |",
        f"| Archivos ilegibles | {t.archivosIlegibles} |",
        f"| CatalogFile | {t.catalogFiles} |",
        f"| LearningElement | {t.learningElements} |",
        f"| Backing | {t.backings} |",
        f"| Usage | {t.usages} |",
        f"| Provenance | {t.provenance} |",
        "",
        "## Archivos",
        "",
        "| Archivo | Título en el LMS | Estado | Motivo o advertencias | Recorrido |",
        "| --- | --- | --- | --- | --- |",
    ]
    for f in reporte.archivos:
        notas = "; ".join(([f.motivo] if f.motivo else []) + f.advertencias) or "-"
        lineas.append(
            f"| {f.sourceIdentifier} | {f.tituloLms} | {f.estado} | {notas} | {' → '.join(f.pasos)} |"
        )
    return "\n".join(lineas) + "\n"


def generar_reporte(estado: EstadoLote) -> dict:
    reporte = construir_reporte(estado)
    carpeta = Path(estado["carpetaSalida"])
    (carpeta / "reporte.json").write_text(reporte.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (carpeta / "reporte.md").write_text(reporte_markdown(reporte), encoding="utf-8")
    return {"reporte": reporte}
