"""Arma los dos grafos del agente.

Grafo del lote:
    START → cargar_lote → (un Send por contenido) → procesar_contenido
          → consolidar_lote → escribir_salidas → generar_reporte → END

Subgrafo de un contenido:
    START → revisar_legibilidad → ¿legible?
              sí → resolver_identidad → generar_metadata → proponer_respaldos → armar_objetos
              no → marcar_ilegible → armar_objetos
          → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from indexador.estado import EstadoContenido, EstadoLote, ResultadoContenido
from indexador.nodos.armar_objetos import armar_objetos
from indexador.nodos.cargar_lote import cargar_lote
from indexador.nodos.consolidar_lote import consolidar_lote
from indexador.nodos.escribir_salidas import escribir_salidas
from indexador.nodos.generar_metadata import generar_metadata
from indexador.nodos.generar_reporte import generar_reporte
from indexador.nodos.marcar_ilegible import marcar_ilegible
from indexador.nodos.proponer_respaldos import proponer_respaldos
from indexador.nodos.resolver_identidad import resolver_identidad
from indexador.nodos.revisar_legibilidad import revisar_legibilidad


def es_legible(estado: EstadoContenido) -> str:
    return "resolver_identidad" if estado.get("legible", True) else "marcar_ilegible"


def construir_subgrafo_contenido():
    g = StateGraph(EstadoContenido)
    g.add_node("revisar_legibilidad", revisar_legibilidad)
    g.add_node("resolver_identidad", resolver_identidad)
    g.add_node("generar_metadata", generar_metadata)
    g.add_node("proponer_respaldos", proponer_respaldos)
    g.add_node("marcar_ilegible", marcar_ilegible)
    g.add_node("armar_objetos", armar_objetos)
    g.add_edge(START, "revisar_legibilidad")
    g.add_conditional_edges("revisar_legibilidad", es_legible, ["resolver_identidad", "marcar_ilegible"])
    g.add_edge("resolver_identidad", "generar_metadata")
    g.add_edge("generar_metadata", "proponer_respaldos")
    g.add_edge("proponer_respaldos", "armar_objetos")
    g.add_edge("marcar_ilegible", "armar_objetos")
    g.add_edge("armar_objetos", END)
    return g.compile()


SUBGRAFO_CONTENIDO = construir_subgrafo_contenido()


def repartir(estado: EstadoLote) -> list[Send]:
    return [
        Send(
            "procesar_contenido",
            {
                "contenido": contenido,
                "entrada": estado["entrada"],
                "config": estado["config"],
                "ahora": estado["inicio"],
            },
        )
        for contenido in estado["contenidos"]
    ]


def procesar_contenido(estado: EstadoContenido) -> dict:
    final = SUBGRAFO_CONTENIDO.invoke(estado)
    resultado: ResultadoContenido = {
        "contenido": final["contenido"],
        "legible": final.get("legible", True),
        "motivo": final.get("motivo"),
        "advertencias": final.get("advertencias", []),
        "pasos": final.get("pasos", []),
        "objetos": final["objetos"],
    }
    return {"resultados": [resultado]}


def construir_grafo_lote():
    g = StateGraph(EstadoLote)
    g.add_node("cargar_lote", cargar_lote)
    g.add_node("procesar_contenido", procesar_contenido)
    g.add_node("consolidar_lote", consolidar_lote)
    g.add_node("escribir_salidas", escribir_salidas)
    g.add_node("generar_reporte", generar_reporte)
    g.add_edge(START, "cargar_lote")
    g.add_conditional_edges("cargar_lote", repartir, ["procesar_contenido"])
    g.add_edge("procesar_contenido", "consolidar_lote")
    g.add_edge("consolidar_lote", "escribir_salidas")
    g.add_edge("escribir_salidas", "generar_reporte")
    g.add_edge("generar_reporte", END)
    return g.compile()


GRAFO_LOTE = construir_grafo_lote()
