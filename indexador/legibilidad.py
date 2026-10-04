"""Reglas para decidir si un contenido se puede leer. Sin LangGraph: se prueban solas."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from indexador.esquemas.entrada import ESTADOS_CON_MARKDOWN, ArchivoEntrada

MOTIVOS_DEL_CORE = {
    "unsupported": "El core no convierte este tipo de archivo a Markdown.",
    "failed": "El core no pudo leer el archivo: está corrupto, protegido o es un escaneo sin texto.",
    "too_large": "El archivo supera el tamaño máximo que el core convierte.",
    "skipped_limit": "El core no lo convirtió porque se agotó el presupuesto de conversiones de la consulta.",
}

_ENCABEZADO_DE_PAGINA = re.compile(r"(?m)^\s*#{1,6}\s*Página\s+\d+\s*$")
_SINTAXIS_Y_ESPACIOS = re.compile(r"[\s#*|>\-`_]+")


def caracteres_utiles(markdown: str) -> int:
    """Caracteres de texto real: sin encabezados de página del conversor PDF, sintaxis ni espacios."""
    sin_paginas = _ENCABEZADO_DE_PAGINA.sub("", markdown)
    return len(_SINTAXIS_Y_ESPACIOS.sub("", sin_paginas))


@dataclass
class Legibilidad:
    legible: bool
    markdown: Optional[str] = None
    motivo: Optional[str] = None
    advertencias: list[str] = field(default_factory=list)


def evaluar(archivo: ArchivoEntrada, carpeta_lote: Path, min_caracteres: int) -> Legibilidad:
    """Decide si el contenido de un archivo se puede leer y, si no, por qué."""
    estado = archivo.core.markdownStatus
    if estado not in ESTADOS_CON_MARKDOWN:
        advertencias = [f"Aviso del core: {archivo.core.markdownWarning}"] if archivo.core.markdownWarning else []
        return Legibilidad(legible=False, motivo=MOTIVOS_DEL_CORE[estado], advertencias=advertencias)

    ruta = carpeta_lote / archivo.markdownPath
    try:
        markdown = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return Legibilidad(legible=False, motivo=f"No se pudo leer el markdown ({type(error).__name__}).")

    utiles = caracteres_utiles(markdown)
    if utiles < min_caracteres:
        return Legibilidad(
            legible=False,
            markdown=markdown,
            motivo=(
                f"El markdown tiene {utiles} caracteres de texto, menos que el mínimo de {min_caracteres}: "
                "probablemente es un escaneo sin texto."
            ),
        )

    advertencias = []
    if archivo.core.markdownTruncated:
        advertencias.append("El core truncó el markdown: la metadata se genera solo con la parte disponible.")
    return Legibilidad(legible=True, markdown=markdown, advertencias=advertencias)
