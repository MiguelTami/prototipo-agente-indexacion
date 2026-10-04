"""Modelo del reporte de una corrida (reporte.json)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# procesado: generó un elemento nuevo · vinculado: ya existía en el catálogo · ilegible: con motivo.
EstadoArchivo = Literal["procesado", "vinculado", "ilegible"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReporteRespaldo(_Base):
    """El juicio del modelo sobre un RA. La razón vive aquí porque Backing no tiene dónde guardarla."""

    codigoRA: str
    aporta: bool
    caracter: Optional[str] = None
    nivelOfrecido: Optional[str] = None
    confianza: float
    razon: str
    backingId: Optional[str] = None


class ReporteArchivo(_Base):
    sourceIdentifier: str
    tituloLms: str
    contentHash: str
    estado: EstadoArchivo
    learningElementId: Optional[str] = None
    motivo: Optional[str] = Field(default=None, description="Por qué es ilegible, en lenguaje natural.")
    advertencias: list[str] = Field(default_factory=list)
    pasos: list[str] = Field(default_factory=list, description="Nodos del grafo que recorrió su contenido.")
    objetos: dict[str, list[str]] = Field(
        default_factory=dict, description="Ids generados por tipo de objeto."
    )
    respaldos: list[ReporteRespaldo] = Field(default_factory=list)


class Totales(_Base):
    archivosRecibidos: int = 0
    contenidosUnicos: int = 0
    archivosProcesados: int = 0
    archivosVinculados: int = 0
    archivosIlegibles: int = 0
    catalogFiles: int = 0
    learningElements: int = 0
    backings: int = 0
    backingsPorCaracter: dict[str, int] = Field(default_factory=dict)
    usages: int = 0
    provenance: int = 0
    tokensEntrada: int = 0
    tokensSalida: int = 0
    duracionSegundos: float = 0.0


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
