"""Nodo marcar_ilegible. Esqueleto del paso 2: solo registra que el contenido pasó por aquí."""

from __future__ import annotations

from indexador.estado import EstadoContenido


def marcar_ilegible(estado: EstadoContenido) -> dict:
    return {"pasos": ["marcar_ilegible"]}
