"""Nodo generar_metadata. Esqueleto del paso 2: solo registra que el contenido pasó por aquí."""

from __future__ import annotations

from indexador.estado import EstadoContenido


def generar_metadata(estado: EstadoContenido) -> dict:
    return {"pasos": ["generar_metadata"]}
