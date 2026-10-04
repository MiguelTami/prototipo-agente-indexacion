"""Modelo del reporte de una corrida (reporte.json)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# "sin_procesar" existe mientras los nodos del grafo no están implementados.
EstadoArchivo = Literal["procesado", "ilegible", "sin_procesar"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReporteArchivo(_Base):
    sourceIdentifier: str
    tituloLms: str
    contentHash: str
    estado: EstadoArchivo
    motivo: Optional[str] = Field(default=None, description="Por qué es ilegible, en lenguaje natural.")
    advertencias: list[str] = Field(default_factory=list)
    pasos: list[str] = Field(default_factory=list, description="Nodos del grafo que recorrió su contenido.")
    objetos: dict[str, list[str]] = Field(
        default_factory=dict, description="Ids generados por tipo de objeto."
    )


class Totales(_Base):
    archivosRecibidos: int = 0
    contenidosUnicos: int = 0
    archivosProcesados: int = 0
    archivosIlegibles: int = 0
    catalogFiles: int = 0
    learningElements: int = 0
    backings: int = 0
    usages: int = 0
    provenance: int = 0


class Reporte(_Base):
    runId: str
    inicio: str
    fin: str
    agentVersion: str
    configVersion: str
    modoLlm: str
    modeloLlm: Optional[str] = None
    lote: str
    offeringId: str
    totales: Totales
    archivos: list[ReporteArchivo]
