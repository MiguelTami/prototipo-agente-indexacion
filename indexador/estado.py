"""Estado de los dos grafos: el del lote y el de cada contenido.

Un "contenido" es un grupo de archivos del lote con el mismo contentHash: se procesa una sola
vez y genera un elemento con un uso por archivo (un archivo en 40 secciones es un elemento con
40 usos).
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from indexador.config import Config
from indexador.esquemas.entrada import ArchivoEntrada, EntradaLote
from indexador.esquemas.reporte import Reporte
from indexador.esquemas.salida import ObjetosCorrida
from indexador.llm import JuicioRespaldo, MetadataPropuesta


class Contenido(TypedDict):
    contentHash: str
    archivos: list[ArchivoEntrada]


class EstadoContenido(TypedDict, total=False):
    """Estado del subgrafo: viaja con un contenido de principio a fin."""

    # Entrada del subgrafo (la manda el Send del lote).
    contenido: Contenido
    entrada: EntradaLote
    config: Config
    ahora: str
    # Lo que van llenando los nodos.
    markdown: Optional[str]
    legible: bool
    motivo: Optional[str]
    learningElementId: str
    elementoExistente: bool
    metadata: MetadataPropuesta
    juicios: list[JuicioRespaldo]
    modelo: str
    tokensEntrada: Annotated[int, operator.add]
    tokensSalida: Annotated[int, operator.add]
    advertencias: Annotated[list[str], operator.add]
    pasos: Annotated[list[str], operator.add]
    objetos: ObjetosCorrida


class ResultadoContenido(TypedDict):
    """Lo que devuelve el subgrafo al lote por cada contenido."""

    contenido: Contenido
    legible: bool
    motivo: Optional[str]
    advertencias: list[str]
    pasos: list[str]
    objetos: ObjetosCorrida
    juicios: list[JuicioRespaldo]
    tokensEntrada: int
    tokensSalida: int


class EstadoLote(TypedDict, total=False):
    """Estado del grafo principal."""

    entrada: EntradaLote
    config: Config
    runId: str
    inicio: str
    carpetaSalida: str
    contenidos: list[Contenido]
    resultados: Annotated[list[ResultadoContenido], operator.add]
    objetos: ObjetosCorrida
    reporte: Reporte
