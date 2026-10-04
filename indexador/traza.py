"""Traza de una corrida: qué devolvió cada nodo del subgrafo, contenido por contenido.

Sirve para ver el agente funcionando sin abrir un depurador. Los valores grandes (el markdown)
se resumen y los objetos se cuentan, para que la traza se pueda leer.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from indexador.esquemas.salida import ObjetosCorrida

_OMITIDOS = {"pasos", "entrada", "config", "contenido", "ahora"}


def _resumir_valor(clave: str, valor: Any) -> Any:
    if clave in {"markdown", "markdownElemento"}:
        return None if valor is None else f"<{len(valor)} caracteres>"
    if isinstance(valor, ObjetosCorrida):
        return {
            campo: [o.id for o in getattr(valor, campo)]
            for campo in ("catalogFiles", "learningElements", "backings", "usages")
            if getattr(valor, campo)
        } | ({"provenance": len(valor.provenance)} if valor.provenance else {})
    if isinstance(valor, BaseModel):
        return valor.model_dump(mode="json")
    if isinstance(valor, list):
        return [_resumir_valor(clave, v) for v in valor]
    return valor


def resumir_salida(cambios: dict) -> dict:
    """Lo que devolvió un nodo, listo para leer o serializar."""
    return {k: _resumir_valor(k, v) for k, v in cambios.items() if k not in _OMITIDOS}


def traza_markdown(entradas: list[dict]) -> str:
    """entradas: [{sourceIdentifiers, tituloLms, pasos: [{nodo, salida}]}] en el orden del lote."""
    lineas = ["# Traza nodo por nodo", ""]
    for entrada in entradas:
        ids = ", ".join(entrada["sourceIdentifiers"])
        lineas += [f"## {ids} · {entrada['tituloLms']}", ""]
        for paso in entrada["pasos"]:
            lineas.append(f"### {paso['nodo']}")
            lineas.append("")
            if paso["salida"]:
                lineas += ["```json", json.dumps(paso["salida"], ensure_ascii=False, indent=2), "```"]
            else:
                lineas.append("(sin cambios)")
            lineas.append("")
    return "\n".join(lineas)


def _corto(valor: Any, limite: int = 110) -> str:
    texto = json.dumps(valor, ensure_ascii=False) if not isinstance(valor, str) else valor
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def traza_terminal(entradas: list[dict]) -> str:
    """Versión compacta para la terminal: una línea por dato que devolvió cada nodo."""
    lineas = []
    for entrada in entradas:
        lineas.append(f"\n=== {', '.join(entrada['sourceIdentifiers'])} · {entrada['tituloLms']}")
        for paso in entrada["pasos"]:
            salida = {k: v for k, v in paso["salida"].items() if v not in (None, [], {})}
            lineas.append(f"  {paso['nodo']}")
            for clave, valor in salida.items():
                if clave == "metadata":
                    for campo, v in valor.items():
                        lineas.append(f"      metadata.{campo}: {_corto(v)}")
                elif clave == "juicios":
                    for j in valor:
                        marca = f"aporta ({j['caracter']}, {j['confianza']:.2f})" if j["aporta"] else f"no aporta ({j['confianza']:.2f})"
                        lineas.append(f"      {j['codigoRA']}: {marca} · {_corto(j['razon'], 80)}")
                else:
                    lineas.append(f"      {clave}: {_corto(valor)}")
    return "\n".join(lineas)
