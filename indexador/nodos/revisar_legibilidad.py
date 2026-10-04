"""Nodo revisar_legibilidad. Esqueleto del paso 2: solo registra que el contenido pasó por aquí."""

from __future__ import annotations

from indexador.estado import EstadoContenido


def revisar_legibilidad(estado: EstadoContenido) -> dict:
    return {"pasos": ["revisar_legibilidad"]}
