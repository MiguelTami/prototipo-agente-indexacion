"""Arma el reporte de la corrida y lo escribe en JSON (máquinas) y en markdown (personas)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from indexador.esquemas.reporte import Reporte, ReporteArchivo, ReporteRespaldo, Totales
from indexador.estado import EstadoLote, ResultadoContenido
from indexador.objetos import id_backing
from indexador.traza import traza_markdown


def _estado_archivo(resultado: ResultadoContenido) -> str:
    if not resultado["legible"]:
        return "ilegible"
    return "vinculado" if resultado.get("elementoExistente") else "procesado"


def _ids_por_archivo(resultado: ResultadoContenido, source_identifier: str) -> dict[str, list[str]]:
    objetos = resultado["objetos"]
    ids: dict[str, list[str]] = {
        "catalogFiles": [c.id for c in objetos.catalogFiles if c.sourceIdentifier == source_identifier],
        "learningElements": [e.id for e in objetos.learningElements],
        "backings": [b.id for b in objetos.backings],
        "usages": [u.id for u in objetos.usages if u.id == f"us-{source_identifier}"],
    }
    return {tipo: lista for tipo, lista in ids.items() if lista}


def _respaldos(resultado: ResultadoContenido) -> list[ReporteRespaldo]:
    creados = {b.id for b in resultado["objetos"].backings}
    le_id = resultado.get("learningElementId") or ""
    filas = []
    for juicio in resultado.get("juicios", []):
        backing_id = id_backing(le_id, juicio.codigoRA)
        filas.append(
            ReporteRespaldo(
                codigoRA=juicio.codigoRA,
                aporta=juicio.aporta,
                caracter=juicio.caracter,
                nivelOfrecido=juicio.nivelOfrecido,
                confianza=juicio.confianza,
                razon=juicio.razon,
                backingId=backing_id if backing_id in creados else None,
            )
        )
    return filas


def construir_reporte(estado: EstadoLote) -> Reporte:
    entrada, config, objetos = estado["entrada"], estado["config"], estado["objetos"]
    resultados = estado.get("resultados", [])
    filas: list[ReporteArchivo] = []
    for resultado in resultados:
        for archivo in resultado["contenido"]["archivos"]:
            filas.append(
                ReporteArchivo(
                    sourceIdentifier=archivo.sourceIdentifier,
                    tituloLms=archivo.tituloLms,
                    contentHash=archivo.core.contentHash,
                    estado=_estado_archivo(resultado),
                    learningElementId=resultado.get("learningElementId") if resultado["legible"] else None,
                    motivo=resultado["motivo"],
                    advertencias=resultado["advertencias"],
                    pasos=resultado["pasos"],
                    objetos=_ids_por_archivo(resultado, archivo.sourceIdentifier),
                    respaldos=_respaldos(resultado),
                )
            )
    orden = {a.sourceIdentifier: i for i, a in enumerate(entrada.lote.archivos)}
    filas.sort(key=lambda f: orden[f.sourceIdentifier])

    fin = datetime.now(timezone.utc)
    modelos = sorted({r["modelo"] for r in resultados if r.get("modelo")})
    totales = Totales(
        archivosRecibidos=len(entrada.lote.archivos),
        contenidosUnicos=len(estado.get("contenidos", [])),
        archivosProcesados=sum(f.estado == "procesado" for f in filas),
        archivosVinculados=sum(f.estado == "vinculado" for f in filas),
        archivosIlegibles=sum(f.estado == "ilegible" for f in filas),
        catalogFiles=len(objetos.catalogFiles),
        learningElements=len(objetos.learningElements),
        backings=len(objetos.backings),
        backingsPorCaracter=dict(sorted(Counter(b.character for b in objetos.backings).items())),
        usages=len(objetos.usages),
        provenance=len(objetos.provenance),
        tokensEntrada=sum(r.get("tokensEntrada", 0) for r in resultados),
        tokensSalida=sum(r.get("tokensSalida", 0) for r in resultados),
        duracionSegundos=round((fin - datetime.fromisoformat(estado["inicio"])).total_seconds(), 2),
    )
    return Reporte(
        runId=estado["runId"],
        inicio=estado["inicio"],
        fin=fin.isoformat(timespec="seconds"),
        agentVersion=config.agentVersion,
        configVersion=config.configVersion,
        modoLlm=config.llm.modo,
        modeloLlm=", ".join(modelos) or config.llm.modelo,
        lote=entrada.lote.descripcion,
        offeringId=entrada.lote.offeringId,
        totales=totales,
        archivos=filas,
    )


def _celda(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")


def reporte_markdown(reporte: Reporte) -> str:
    t = reporte.totales
    caracteres = ", ".join(f"{k} {v}" for k, v in t.backingsPorCaracter.items()) or "-"
    lineas = [
        f"# Reporte de indexación {reporte.runId}",
        "",
        f"- **Curso dictado:** {reporte.offeringId}",
        f"- **Inicio / fin:** {reporte.inicio} / {reporte.fin} ({t.duracionSegundos} s)",
        f"- **Agente:** {reporte.agentVersion} · configuración {reporte.configVersion}",
        f"- **LLM:** {reporte.modoLlm}" + (f" ({reporte.modeloLlm})" if reporte.modeloLlm else ""),
        f"- **Tokens:** {t.tokensEntrada} de entrada, {t.tokensSalida} de salida",
        "",
        "## Totales",
        "",
        "| Medida | Valor |",
        "| --- | --- |",
        f"| Archivos recibidos | {t.archivosRecibidos} |",
        f"| Contenidos únicos | {t.contenidosUnicos} |",
        f"| Archivos procesados (elemento nuevo) | {t.archivosProcesados} |",
        f"| Archivos vinculados a un elemento existente | {t.archivosVinculados} |",
        f"| Archivos ilegibles | {t.archivosIlegibles} |",
        f"| CatalogFile | {t.catalogFiles} |",
        f"| LearningElement | {t.learningElements} |",
        f"| Backing propuestos | {t.backings} ({caracteres}) |",
        f"| Usage | {t.usages} |",
        f"| Provenance | {t.provenance} |",
        "",
        "## Archivos",
        "",
        "| Archivo | Título en el LMS | Estado | Elemento | Motivo o advertencias |",
        "| --- | --- | --- | --- | --- |",
    ]
    for f in reporte.archivos:
        notas = "; ".join(([f.motivo] if f.motivo else []) + f.advertencias) or "-"
        lineas.append(
            f"| {f.sourceIdentifier} | {_celda(f.tituloLms)} | {f.estado} | {f.learningElementId or '-'} | {_celda(notas)} |"
        )

    lineas += [
        "",
        "## Respaldos propuestos",
        "",
        "Solo los RA a los que el modelo dijo que el elemento aporta. Todos quedan en estado Proposed.",
        "",
        "| Elemento | RA | Carácter | Nivel ofrecido | Confianza | Razón |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    vistos = set()
    for f in reporte.archivos:
        if f.learningElementId in vistos or f.estado != "procesado":
            continue
        vistos.add(f.learningElementId)
        for r in f.respaldos:
            if r.aporta:
                lineas.append(
                    f"| {f.learningElementId} | {r.codigoRA} | {r.caracter} | {r.nivelOfrecido or '-'} "
                    f"| {r.confianza:.2f} | {_celda(r.razon)} |"
                )

    lineas += ["", "## Recorrido por el grafo", "", "| Archivo | Nodos |", "| --- | --- |"]
    for f in reporte.archivos:
        lineas.append(f"| {f.sourceIdentifier} | {' → '.join(f.pasos)} |")
    return "\n".join(lineas) + "\n"


def generar_reporte(estado: EstadoLote) -> dict:
    reporte = construir_reporte(estado)
    carpeta = Path(estado["carpetaSalida"])
    (carpeta / "reporte.json").write_text(reporte.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (carpeta / "reporte.md").write_text(reporte_markdown(reporte), encoding="utf-8")
    if estado.get("trazar"):
        escribir_traza(estado, carpeta)
    return {"reporte": reporte}


def escribir_traza(estado: EstadoLote, carpeta: Path) -> None:
    """traza.json y traza.md, en el orden del manifiesto."""
    orden = {a.sourceIdentifier: i for i, a in enumerate(estado["entrada"].lote.archivos)}
    entradas = [
        {
            "sourceIdentifiers": [a.sourceIdentifier for a in r["contenido"]["archivos"]],
            "tituloLms": r["contenido"]["archivos"][0].tituloLms,
            "pasos": r.get("traza", []),
        }
        for r in estado.get("resultados", [])
    ]
    entradas.sort(key=lambda e: orden[e["sourceIdentifiers"][0]])
    (carpeta / "traza.json").write_text(json.dumps(entradas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (carpeta / "traza.md").write_text(traza_markdown(entradas), encoding="utf-8")
