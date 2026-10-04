"""Prototipo del agente de indexación de Learning Catalog.

Un único llamado procesa un lote completo:

    from indexador import indexar
    resultado = indexar("ejemplos/curso-412711", "salida")
"""

from __future__ import annotations

__version__ = "0.1.0"

from indexador.corrida import ResultadoCorrida, indexar

__all__ = ["ResultadoCorrida", "indexar", "__version__"]
