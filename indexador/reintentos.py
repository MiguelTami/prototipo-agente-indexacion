"""Reintentos de una llamada al modelo, sin dejar que un fallo corte la corrida."""

from __future__ import annotations

from typing import Callable, TypeVar

from indexador.llm import ErrorModelo

T = TypeVar("T")


def con_reintentos(llamada: Callable[[], T], reintentos: int) -> tuple[T | None, list[str]]:
    """Ejecuta la llamada hasta 1 + reintentos veces. Devuelve el valor (o None) y los errores vistos."""
    errores: list[str] = []
    for _ in range(reintentos + 1):
        try:
            return llamada(), errores
        except ErrorModelo as error:
            errores.append(str(error))
    return None, errores
