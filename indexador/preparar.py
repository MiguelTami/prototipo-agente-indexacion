"""Prepara un lote del agente a partir de una carpeta de PDF reales.

Hace, fuera de uP1, lo que en la plataforma hace el core al convertir un archivo a Markdown
(object-manager/docs/features/markdown-conversion.md):
- texto por página, con una sección "## Página N" por página;
- contentHash = sha256 de los bytes del PDF;
- los mismos estados: ok, failed (corrupto, protegido o sin texto) y too_large;
- los mismos topes por defecto: 15 MB, 200 páginas y 500 000 caracteres (luego trunca).

Uso:
    python -m indexador.preparar --pdfs lotes-reales/mi-curso/pdfs --salida lotes-reales/mi-curso --curso "Nombre del curso"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from indexador.esquemas.entrada import cargar_entrada

MAX_BYTES = 15 * 1024 * 1024
MAX_PAGINAS = 200
MAX_CARACTERES = 500_000

AVISO_FALLIDO = "El archivo no se pudo leer (corrupto, protegido o escaneado sin texto): una IA no podrá leer este documento."
AVISO_GRANDE = "El archivo supera el tope de conversión: una IA no podrá leer este documento."
AVISO_TRUNCADO = "El contenido superó el tope de caracteres y se truncó."
NOTA = "Archivo real. Markdown generado por indexador.preparar, que imita el conversor PDF del core."


def _orden_natural(ruta: Path) -> list:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", ruta.name)]


def _modulo(nombre: str, posicion: int) -> str:
    """'Semana N' si el nombre del archivo la menciona; si no, la posición en la carpeta."""
    coincidencia = re.search(r"semana[\s_\-]*0*(\d+)", nombre, re.IGNORECASE)
    return f"Semana {coincidencia.group(1)}" if coincidencia else f"Archivo {posicion}"


def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-") or "archivo"


def convertir_pdf(datos: bytes) -> tuple[str, Optional[str], Optional[str], bool]:
    """Devuelve (estado, markdown, aviso, truncado) con la lógica del conversor del core."""
    try:
        import pdfplumber
    except ImportError as error:  # pragma: no cover - depende de la instalación
        raise SystemExit('Falta pdfplumber: pip install -e ".[pdf]"') from error
    import io

    if len(datos) > MAX_BYTES:
        return "too_large", None, AVISO_GRANDE, False
    try:
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            if len(pdf.pages) > MAX_PAGINAS:
                return "too_large", None, AVISO_GRANDE, False
            paginas = [(pagina.extract_text() or "").strip() for pagina in pdf.pages]
    except Exception:  # pdfminer lanza muchos tipos distintos ante un PDF dañado o protegido
        return "failed", None, AVISO_FALLIDO, False
    if not any(paginas):
        return "failed", None, AVISO_FALLIDO, False
    markdown = "\n\n".join(f"## Página {i}\n\n{texto}" for i, texto in enumerate(paginas, start=1)) + "\n"
    if len(markdown) > MAX_CARACTERES:
        return "ok", markdown[:MAX_CARACTERES], AVISO_TRUNCADO, True
    return "ok", markdown, None, False


def preparar_lote(
    carpeta_pdfs: str | Path,
    salida: str | Path,
    curso: str,
    ras: Optional[str | Path] = None,
    forzar: bool = False,
) -> Path:
    """Convierte los PDF de una carpeta y escribe un lote listo para indexar()."""
    carpeta_pdfs, salida = Path(carpeta_pdfs), Path(salida)
    pdfs = sorted((p for p in carpeta_pdfs.iterdir() if p.suffix.lower() == ".pdf"), key=_orden_natural)
    if not pdfs:
        raise SystemExit(f"No hay archivos .pdf en {carpeta_pdfs}")
    if (salida / "lote.json").exists() and not forzar:
        raise SystemExit(f"Ya existe {salida / 'lote.json'}; usa --forzar para reemplazarlo")

    (salida / "archivos").mkdir(parents=True, exist_ok=True)
    (salida / "contexto").mkdir(parents=True, exist_ok=True)
    offering_id = f"off-{_slug(curso)}"

    archivos = []
    for posicion, pdf in enumerate(pdfs, start=1):
        datos = pdf.read_bytes()
        estado, markdown, aviso, truncado = convertir_pdf(datos)
        markdown_path = None
        if markdown is not None:
            markdown_path = f"archivos/{posicion:02d}-{_slug(pdf.stem)}.md"
            (salida / markdown_path).write_text(markdown, encoding="utf-8")
        archivos.append(
            {
                "sourceIdentifier": f"pdf-{posicion:02d}",
                "tituloLms": pdf.stem,
                "fileType": "Pdf",
                "sourceUrl": None,
                "sourceVersion": datetime.fromtimestamp(pdf.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                "modulo": _modulo(pdf.stem, posicion),
                "orden": posicion,
                "markdownPath": markdown_path,
                "core": {
                    "filename": pdf.name,
                    "contentHash": hashlib.sha256(datos).hexdigest(),
                    "markdownStatus": estado,
                    "markdownWarning": aviso,
                    "markdownTruncated": truncado,
                },
                "sintetico": False,
                "notaSimulacion": NOTA,
            }
        )

    resultados = json.loads(Path(ras).read_text(encoding="utf-8")) if ras else []
    contexto = {
        "curso": {"id": f"act-{_slug(curso)}", "name": curso},
        "cursoDictado": {"id": offering_id, "lmsId": _slug(curso), "name": curso},
        "resultadosAprendizaje": resultados,
    }
    lote = {
        "version": 1,
        "descripcion": f"Lote real: {len(pdfs)} PDF de {carpeta_pdfs}, convertidos con indexador.preparar.",
        "tenant": "LOCAL",
        "sourceSystem": "Lms",
        "lms": "Archivos locales",
        "offeringId": offering_id,
        "archivos": archivos,
    }
    (salida / "contexto" / "curso.json").write_text(json.dumps(contexto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (salida / "lote.json").write_text(json.dumps(lote, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cargar_entrada(salida)  # el lote generado tiene que ser válido
    return salida


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="indexador.preparar", description="Arma un lote del agente a partir de PDF")
    parser.add_argument("--pdfs", required=True, help="Carpeta con los PDF")
    parser.add_argument("--salida", required=True, help="Carpeta donde se escribe el lote")
    parser.add_argument("--curso", required=True, help="Nombre del curso")
    parser.add_argument("--ras", default=None, help="JSON opcional con los RA: [{id, code, name, bloomLevel}]")
    parser.add_argument("--forzar", action="store_true", help="Reemplaza un lote existente")
    args = parser.parse_args(argv)

    carpeta = preparar_lote(args.pdfs, args.salida, args.curso, args.ras, args.forzar)
    lote = json.loads((carpeta / "lote.json").read_text(encoding="utf-8"))
    print(f"Lote listo en {carpeta}")
    for a in lote["archivos"]:
        print(f"  {a['sourceIdentifier']}  {a['modulo']:12}  {a['core']['markdownStatus']:10}  {a['core']['filename']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
