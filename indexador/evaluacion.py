"""Compara una corrida con las respuestas esperadas y mide el acuerdo por campo.

Lee lo que la corrida dejó en disco (reporte.json y objetos/learning_elements.json), no el estado
en memoria: así evalúa cualquier corrida, de hoy o de antes, y con cualquier modelo.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from indexador.esquemas.esperado import RespuestasEsperadas, cargar_esperado
from indexador.esquemas.reporte import Reporte

# Orden en que se muestran los campos.
CAMPOS = [
    "estado",
    "mismoElemento",
    "cognitiveLevel",
    "knowledgeType",
    "language",
    "identifiedAuthors",
    "terminosClave",
    "estimatedTime",
    "tituloDescriptivo",
    "respaldo.aporta",
    "respaldo.caracter",
]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Acuerdo(_Base):
    aciertos: int = 0
    total: int = 0

    @property
    def porcentaje(self) -> Optional[float]:
        return round(100 * self.aciertos / self.total, 1) if self.total else None


class Desacuerdo(_Base):
    sourceIdentifier: str
    campo: str
    esperado: Any
    obtenido: Any


class Evaluacion(_Base):
    runId: str
    modelo: Optional[str]
    estadoEsperado: str = Field(description="borrador o revisado")
    campos: dict[str, Acuerdo]
    desacuerdos: list[Desacuerdo]
    sinRespuestaEsperada: list[str] = Field(default_factory=list)


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


class _Registro:
    def __init__(self) -> None:
        self.campos = {campo: Acuerdo() for campo in CAMPOS}
        self.desacuerdos: list[Desacuerdo] = []

    def anotar(self, source_identifier: str, campo: str, acierto: bool, esperado: Any, obtenido: Any) -> None:
        self.campos[campo].total += 1
        if acierto:
            self.campos[campo].aciertos += 1
        else:
            self.desacuerdos.append(
                Desacuerdo(sourceIdentifier=source_identifier, campo=campo, esperado=esperado, obtenido=obtenido)
            )


def evaluar(carpeta_corrida: str | Path, esperado: RespuestasEsperadas | str | Path) -> Evaluacion:
    carpeta = Path(carpeta_corrida)
    if not isinstance(esperado, RespuestasEsperadas):
        esperado = cargar_esperado(esperado)
    reporte = Reporte.model_validate_json((carpeta / "reporte.json").read_text(encoding="utf-8"))
    elementos = {
        e["id"]: e for e in json.loads((carpeta / "objetos" / "learning_elements.json").read_text(encoding="utf-8"))
    }
    archivos = {f.sourceIdentifier: f for f in reporte.archivos}
    registro = _Registro()

    for sid, esp in esperado.archivos.items():
        obtenido = archivos.get(sid)
        if obtenido is None:
            registro.anotar(sid, "estado", False, esp.estado, "no está en la corrida")
            continue
        registro.anotar(sid, "estado", obtenido.estado == esp.estado, esp.estado, obtenido.estado)

        if esp.mismoElementoQue:
            otro = archivos.get(esp.mismoElementoQue)
            iguales = bool(otro and obtenido.learningElementId and otro.learningElementId == obtenido.learningElementId)
            registro.anotar(
                sid, "mismoElemento", iguales, esp.mismoElementoQue, obtenido.learningElementId
            )

        elemento = elementos.get(obtenido.learningElementId or "")
        if not esp.elemento or obtenido.estado != "procesado" or elemento is None:
            continue
        e = esp.elemento

        registro.anotar(sid, "cognitiveLevel", elemento["cognitiveLevel"] in e.cognitiveLevel, e.cognitiveLevel, elemento["cognitiveLevel"])
        registro.anotar(sid, "knowledgeType", elemento["knowledgeType"] in e.knowledgeType, e.knowledgeType, elemento["knowledgeType"])
        registro.anotar(sid, "language", _normalizar(elemento["language"]) == _normalizar(e.language), e.language, elemento["language"])

        autores_esp = {_normalizar(a) for a in e.identifiedAuthors}
        autores_obt = {_normalizar(a) for a in elemento["identifiedAuthors"]}
        registro.anotar(sid, "identifiedAuthors", autores_esp == autores_obt, e.identifiedAuthors, elemento["identifiedAuthors"])

        texto = _normalizar(" ".join(elemento["keywords"]) + " " + elemento["descriptiveTitle"])
        encontrados = [t for t in e.terminosClave if _normalizar(t) in texto]
        registro.anotar(sid, "terminosClave", bool(encontrados), e.terminosClave, elemento["keywords"])

        minimo, maximo = e.estimatedTimeHoras
        registro.anotar(sid, "estimatedTime", minimo <= elemento["estimatedTime"] <= maximo, [minimo, maximo], elemento["estimatedTime"])

        descriptivo = _normalizar(elemento["descriptiveTitle"]) != _normalizar(obtenido.tituloLms)
        registro.anotar(sid, "tituloDescriptivo", descriptivo, f"distinto de «{obtenido.tituloLms}»", elemento["descriptiveTitle"])

        juicios = {r.codigoRA: r for r in obtenido.respaldos}
        for codigo, resp in e.respaldos.items():
            if resp.aporta is None:
                continue
            juicio = juicios.get(codigo)
            aporta = bool(juicio and juicio.aporta)
            registro.anotar(sid, "respaldo.aporta", aporta == resp.aporta, f"{codigo}: {resp.aporta}", f"{codigo}: {aporta}")
            if resp.aporta and aporta:
                registro.anotar(
                    sid, "respaldo.caracter", juicio.caracter in resp.caracteres,
                    f"{codigo}: {' o '.join(resp.caracteres)}", f"{codigo}: {juicio.caracter}",
                )

    return Evaluacion(
        runId=reporte.runId,
        modelo=reporte.modeloLlm,
        estadoEsperado=esperado.estado,
        campos=registro.campos,
        desacuerdos=registro.desacuerdos,
        sinRespuestaEsperada=sorted(set(archivos) - set(esperado.archivos)),
    )


def _celda(valor: Any) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    return texto.replace("|", "\\|")


def evaluacion_markdown(evaluacion: Evaluacion) -> str:
    lineas = [
        f"# Evaluación de la corrida {evaluacion.runId}",
        "",
        f"- **Modelo:** {evaluacion.modelo or '-'}",
        f"- **Respuestas esperadas:** {evaluacion.estadoEsperado}",
        "",
        "## Acuerdo por campo",
        "",
        "| Campo | Aciertos | Total | Acuerdo |",
        "| --- | --- | --- | --- |",
    ]
    for campo, acuerdo in evaluacion.campos.items():
        if acuerdo.total:
            lineas.append(f"| {campo} | {acuerdo.aciertos} | {acuerdo.total} | {acuerdo.porcentaje} % |")
    lineas += ["", "## Desacuerdos", ""]
    if not evaluacion.desacuerdos:
        lineas.append("Ninguno.")
    else:
        lineas += ["| Archivo | Campo | Esperado | Obtenido |", "| --- | --- | --- | --- |"]
        for d in evaluacion.desacuerdos:
            lineas.append(f"| {d.sourceIdentifier} | {d.campo} | {_celda(d.esperado)} | {_celda(d.obtenido)} |")
    if evaluacion.sinRespuestaEsperada:
        lineas += ["", f"Archivos sin respuesta esperada: {', '.join(evaluacion.sinRespuestaEsperada)}."]
    return "\n".join(lineas) + "\n"


def escribir_evaluacion(evaluacion: Evaluacion, carpeta_corrida: str | Path) -> None:
    carpeta = Path(carpeta_corrida)
    datos = evaluacion.model_dump(mode="json")
    for campo, acuerdo in evaluacion.campos.items():
        datos["campos"][campo]["porcentaje"] = acuerdo.porcentaje
    (carpeta / "evaluacion.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (carpeta / "evaluacion.md").write_text(evaluacion_markdown(evaluacion), encoding="utf-8")
