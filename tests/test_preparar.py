"""preparar_lote convierte PDF reales en un lote válido, con la lógica del conversor del core."""

from __future__ import annotations

import hashlib
import json

import pytest

pytest.importorskip("pdfplumber")

from indexador import indexar  # noqa: E402
from indexador.esquemas.entrada import cargar_entrada  # noqa: E402
from indexador.preparar import preparar_lote  # noqa: E402


def pdf_minimo(paginas: list[str]) -> bytes:
    """Un PDF válido, sin dependencias, con una línea de texto por página (vacía = sin texto)."""
    objetos: list[bytes] = []
    n = len(paginas)
    hijos = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(f"<< /Type /Pages /Kids [{hijos}] /Count {n} >>".encode())
    fuente = 3 + 2 * n
    for i, texto in enumerate(paginas):
        contenido = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1") if texto else b""
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R "
            f"/Resources << /Font << /F1 {fuente} 0 R >> >> >>".encode()
        )
        objetos.append(b"<< /Length %d >>\nstream\n" % len(contenido) + contenido + b"\nendstream")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    salida, posiciones = bytearray(b"%PDF-1.4\n"), []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % numero + cuerpo + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % p for p in posiciones)
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, inicio_xref)
    return bytes(salida)


TEXTO = "La convivencia escolar se construye entre estudiantes docentes y familias " * 3


@pytest.fixture
def carpeta_pdfs(tmp_path):
    carpeta = tmp_path / "pdfs"
    carpeta.mkdir()
    (carpeta / "Semana 2 - Marco legal.pdf").write_bytes(pdf_minimo([TEXTO, "Segunda pagina " + TEXTO]))
    (carpeta / "Semana 10 - Protocolos.pdf").write_bytes(pdf_minimo(["Protocolos de atencion " + TEXTO]))
    (carpeta / "Semana 1 - Introduccion.pdf").write_bytes(pdf_minimo([TEXTO]))
    (carpeta / "escaneado.pdf").write_bytes(pdf_minimo(["", ""]))
    (carpeta / "danado.pdf").write_bytes(b"%PDF-1.4 esto no es un pdf")
    (carpeta / "notas.txt").write_text("se ignora", encoding="utf-8")
    return carpeta


def test_el_lote_preparado_es_valido_y_ordenado(carpeta_pdfs, tmp_path):
    lote = preparar_lote(carpeta_pdfs, tmp_path / "lote", "Curso de prueba")
    entrada = cargar_entrada(lote)
    archivos = entrada.lote.archivos

    assert [a.tituloLms for a in archivos] == [
        "danado", "escaneado", "Semana 1 - Introduccion", "Semana 2 - Marco legal", "Semana 10 - Protocolos",
    ]
    assert [a.modulo for a in archivos][2:] == ["Semana 1", "Semana 2", "Semana 10"]
    assert all(not a.sintetico and a.fileType == "Pdf" for a in archivos)
    assert entrada.contexto.resultadosAprendizaje == []


def test_hash_real_y_paginas_con_el_formato_del_core(carpeta_pdfs, tmp_path):
    lote = preparar_lote(carpeta_pdfs, tmp_path / "lote", "Curso de prueba")
    archivo = next(a for a in cargar_entrada(lote).lote.archivos if a.modulo == "Semana 2")

    datos = (carpeta_pdfs / "Semana 2 - Marco legal.pdf").read_bytes()
    assert archivo.core.contentHash == hashlib.sha256(datos).hexdigest()
    markdown = (lote / archivo.markdownPath).read_text(encoding="utf-8")
    assert markdown.startswith("## Página 1\n\n") and "## Página 2" in markdown
    assert "convivencia escolar" in markdown


def test_danado_y_escaneado_salen_como_failed(carpeta_pdfs, tmp_path):
    lote = preparar_lote(carpeta_pdfs, tmp_path / "lote", "Curso de prueba")
    estados = {a.tituloLms: a.core for a in cargar_entrada(lote).lote.archivos}
    for nombre in ("danado", "escaneado"):
        assert estados[nombre].markdownStatus == "failed"
        assert "una IA no podrá leer" in estados[nombre].markdownWarning


def test_no_reemplaza_un_lote_existente_sin_forzar(carpeta_pdfs, tmp_path):
    preparar_lote(carpeta_pdfs, tmp_path / "lote", "Curso de prueba")
    with pytest.raises(SystemExit, match="--forzar"):
        preparar_lote(carpeta_pdfs, tmp_path / "lote", "Curso de prueba")
    preparar_lote(carpeta_pdfs, tmp_path / "lote", "Curso de prueba", forzar=True)


def test_el_agente_procesa_el_lote_sin_ra(carpeta_pdfs, tmp_path):
    lote = preparar_lote(carpeta_pdfs, tmp_path / "lote", "Curso de prueba")
    resultado = indexar(lote, tmp_path / "salida")
    t = resultado.reporte.totales

    assert (t.archivosProcesados, t.archivosIlegibles, t.backings) == (3, 2, 0)
    assert t.learningElements == 3 and t.usages == 3
    procesado = next(f for f in resultado.reporte.archivos if f.estado == "procesado")
    assert any("no tiene RA" in a for a in procesado.advertencias)
    usos = json.loads((resultado.carpeta / "objetos" / "usages.json").read_text(encoding="utf-8"))
    assert {u["weekOrUnit"] for u in usos} == {"Semana 1", "Semana 2", "Semana 10"}
