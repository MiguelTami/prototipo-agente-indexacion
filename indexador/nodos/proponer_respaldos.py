"""Nodo proponer_respaldos: el modelo juzga el elemento contra cada RA del curso.

Solo se conservan los juicios sobre RA del curso, uno por RA. Si el modelo falla, el elemento
sigue sin respaldos propuestos y el reporte lo advierte: un respaldo nunca se inventa.
"""

from __future__ import annotations

from indexador.estado import EstadoContenido
from indexador.llm import obtener_modelo
from indexador.reintentos import con_reintentos


def proponer_respaldos(estado: EstadoContenido) -> dict:
    config = estado["config"]
    contexto = estado["entrada"].contexto
    modelo = obtener_modelo(config)
    respuesta, errores = con_reintentos(
        lambda: modelo.juzgar_respaldos(estado["markdown"], estado["metadata"], contexto),
        config.llm.reintentos,
        config.llm.esperaReintentoSegundos,
    )
    if respuesta is None:
        return {
            "pasos": ["proponer_respaldos"],
            "juicios": [],
            "advertencias": [f"No se pudieron proponer respaldos: {errores[-1]}"],
        }

    codigos = {ra.code for ra in contexto.resultadosAprendizaje}
    advertencias = [f"Intento fallido del modelo: {e}" for e in errores]
    juicios, vistos = [], set()
    for juicio in respuesta.valor.juicios:
        if juicio.codigoRA not in codigos:
            advertencias.append(f"El modelo juzgó un RA que no es del curso ({juicio.codigoRA}): se descarta.")
        elif juicio.codigoRA in vistos:
            advertencias.append(f"El modelo juzgó dos veces {juicio.codigoRA}: se conserva el primero.")
        else:
            vistos.add(juicio.codigoRA)
            juicios.append(juicio)
    faltantes = sorted(codigos - vistos)
    if faltantes:
        advertencias.append(f"El modelo no juzgó estos RA: {', '.join(faltantes)}.")
    return {
        "pasos": ["proponer_respaldos"],
        "juicios": juicios,
        "tokensEntrada": respuesta.tokensEntrada,
        "tokensSalida": respuesta.tokensSalida,
        "advertencias": advertencias,
    }
