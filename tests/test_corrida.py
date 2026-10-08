"""El único llamado recorre el grafo de punta a punta y deja la carpeta de salida completa."""

from __future__ import annotations

import json
import subprocess
import sys

from indexador import indexar
from indexador.grafo import GRAFO_LOTE, SUBGRAFO_CONTENIDO

ARCHIVOS_DE_OBJETOS = [
    "catalog_files.json",
    "learning_elements.json",
    "backings.json",
    "usages.json",
    "provenance.json",
]


def test_un_llamado_crea_la_carpeta_de_salida_completa(carpeta_lote, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path)

    assert resultado.carpeta == tmp_path / resultado.runId
    for nombre in ARCHIVOS_DE_OBJETOS:
        filas = json.loads((resultado.carpeta / "objetos" / nombre).read_text(encoding="utf-8"))
        assert isinstance(filas, list)
    assert (resultado.carpeta / "markdown").is_dir()
    assert (resultado.carpeta / "reporte.json").is_file()
    assert (resultado.carpeta / "reporte.md").is_file()


def test_el_reporte_lista_todos_los_archivos_y_agrupa_por_contenido(carpeta_lote, tmp_path):
    reporte = indexar(carpeta_lote, tmp_path).reporte

    assert reporte.totales.archivosRecibidos == 14
    assert reporte.totales.contenidosUnicos == 13, "el programa de curso y su copia son un solo contenido"
    assert [f.sourceIdentifier for f in reporte.archivos][:2] == ["4542265", "4542266"]
    assert all(f.pasos[0] == "revisar_legibilidad" and f.pasos[-1] == "armar_objetos" for f in reporte.archivos)


def test_cada_corrida_tiene_su_propia_carpeta(carpeta_lote, tmp_path):
    primera = indexar(carpeta_lote, tmp_path)
    segunda = indexar(carpeta_lote, tmp_path)

    assert primera.runId != segunda.runId
    assert primera.carpeta.is_dir() and segunda.carpeta.is_dir()


def test_la_terminal_hace_lo_mismo_que_la_funcion(carpeta_lote, tmp_path):
    salida = subprocess.run(
        [sys.executable, "-m", "indexador", "--entrada", str(carpeta_lote), "--salida", str(tmp_path)],
        capture_output=True,
        # La terminal escribe en UTF-8 (__main__.py reconfigura stdout); sin decirlo, Windows
        # decodifica con cp1252 y la "ú" no coincide.
        encoding="utf-8",
        check=True,
    )
    assert "14 archivos, 13 contenidos únicos" in salida.stdout
    assert len([p for p in tmp_path.iterdir() if p.is_dir()]) == 1


def test_forma_de_los_grafos():
    lote = GRAFO_LOTE.get_graph()
    assert {"cargar_lote", "procesar_contenido", "consolidar_lote", "escribir_salidas", "generar_reporte"} <= set(lote.nodes)
    contenido = SUBGRAFO_CONTENIDO.get_graph()
    # LAB-40: la identidad se resuelve antes de decidir por la legibilidad.
    destinos = {e.target for e in contenido.edges if e.source == "revisar_legibilidad"}
    assert destinos == {"resolver_identidad"}
    destinos = {e.target for e in contenido.edges if e.source == "resolver_identidad"}
    assert destinos == {"generar_metadata", "armar_objetos", "marcar_ilegible"}
