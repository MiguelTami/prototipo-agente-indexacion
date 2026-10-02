"""Recalcula core.contentHash de un lote sintético a partir de sus .md.

En un lote real el contentHash es el sha256 del archivo original, que calcula el core al
subirlo. Los lotes de ejemplo no tienen archivos originales, así que el hash se deriva del .md
(normalizado a LF) o, cuando el core no generó markdown, de un texto fijo con el identificador.

Uso:
    python scripts/actualizar_hashes.py ejemplos/curso-412711
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def hash_de_markdown(ruta: Path) -> str:
    contenido = ruta.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(contenido).hexdigest()


def hash_sin_contenido(source_identifier: str) -> str:
    return hashlib.sha256(f"sin-contenido:{source_identifier}".encode()).hexdigest()


def hash_esperado(carpeta: Path, archivo: dict) -> str:
    if archivo.get("markdownPath"):
        return hash_de_markdown(carpeta / archivo["markdownPath"])
    return hash_sin_contenido(archivo["sourceIdentifier"])


def main(carpeta: str) -> None:
    carpeta_lote = Path(carpeta)
    ruta = carpeta_lote / "lote.json"
    lote = json.loads(ruta.read_text(encoding="utf-8"))
    for archivo in lote["archivos"]:
        archivo["core"]["contentHash"] = hash_esperado(carpeta_lote, archivo)
    ruta.write_text(json.dumps(lote, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(lote['archivos'])} hashes actualizados en {ruta}")


if __name__ == "__main__":
    main(sys.argv[1])
