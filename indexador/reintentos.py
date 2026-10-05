"""Reintentos de una llamada al modelo, sin dejar que un fallo corte la corrida."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from indexador.llm import ErrorModelo

T = TypeVar("T")


def con_reintentos(
    llamada: Callable[[], T], reintentos: int, espera: float = 0.0
) -> tuple[T | None, list[str]]:
    """Ejecuta la llamada hasta 1 + reintentos veces. Devuelve el valor (o None) y los errores vistos.

    Entre intentos espera `espera` segundos y la duplica cada vez: un límite de solicitudes por
    minuto (típico de una capa gratuita) se resuelve esperando, no insistiendo.
    """
    errores: list[str] = []
    for intento in range(reintentos + 1):
        if intento and espera:
            time.sleep(espera * 2 ** (intento - 1))
        try:
            return llamada(), errores
        except ErrorModelo as error:
            errores.append(str(error))
    return None, errores
