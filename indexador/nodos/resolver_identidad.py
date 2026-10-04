"""Nodo resolver_identidad. Esqueleto del paso 2: solo registra que el contenido pasó por aquí."""

from __future__ import annotations

from indexador.estado import EstadoContenido


def resolver_identidad(estado: EstadoContenido) -> dict:
    return {"pasos": ["resolver_identidad"]}
