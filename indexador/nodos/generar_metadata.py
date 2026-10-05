"""Nodo generar_metadata: el modelo propone la metadata del elemento.

Si el modelo no devuelve una metadata válida después de los reintentos, el contenido sale como
ilegible con el motivo: nunca se escribe un elemento a medias ni se corta la corrida.
"""

from __future__ import annotations

from indexador.estado import EstadoContenido
from indexador.llm import obtener_modelo
from indexador.reintentos import con_reintentos


def generar_metadata(estado: EstadoContenido) -> dict:
    config = estado["config"]
    modelo = obtener_modelo(config)
    archivo = estado["contenido"]["archivos"][0]
    respuesta, errores = con_reintentos(
        lambda: modelo.generar_metadata(estado["markdown"], archivo, estado["entrada"].contexto),
        config.llm.reintentos,
        config.llm.esperaReintentoSegundos,
    )
    if respuesta is None:
        return {
            "pasos": ["generar_metadata"],
            "modelo": modelo.identificador,
            "legible": False,
            "motivo": (
                f"El modelo no devolvió una metadata válida tras {len(errores)} intentos. "
                f"Último error: {errores[-1]}"
            ),
        }
    advertencias = [f"Intento fallido del modelo: {e}" for e in errores]
    return {
        "pasos": ["generar_metadata"],
        "modelo": modelo.identificador,
        "metadata": respuesta.valor,
        "tokensEntrada": respuesta.tokensEntrada,
        "tokensSalida": respuesta.tokensSalida,
        "advertencias": advertencias,
    }
