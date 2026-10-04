"""Nodo proponer_respaldos. Esqueleto del paso 2: solo registra que el contenido pasó por aquí."""

from __future__ import annotations

from indexador.estado import EstadoContenido


def proponer_respaldos(estado: EstadoContenido) -> dict:
    return {"pasos": ["proponer_respaldos"]}
