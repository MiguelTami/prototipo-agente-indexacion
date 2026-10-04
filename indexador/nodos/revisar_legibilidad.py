"""Nodo revisar_legibilidad: decide si el contenido sigue al enriquecimiento o sale como ilegible.

Todos los archivos de un contenido comparten el mismo contentHash, así que basta con evaluar el
primero. Un archivo ilegible nunca lanza una excepción: es un resultado con su motivo.
"""

from __future__ import annotations

from indexador.estado import EstadoContenido
from indexador.legibilidad import evaluar


def revisar_legibilidad(estado: EstadoContenido) -> dict:
    archivo = estado["contenido"]["archivos"][0]
    resultado = evaluar(
        archivo,
        carpeta_lote=estado["entrada"].carpeta,
        min_caracteres=estado["config"].umbrales.minCaracteresUtiles,
    )
    return {
        "pasos": ["revisar_legibilidad"],
        "legible": resultado.legible,
        "markdown": resultado.markdown,
        "motivo": resultado.motivo,
        "advertencias": resultado.advertencias,
    }
