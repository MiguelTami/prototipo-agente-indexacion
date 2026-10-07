"""La exportación lleva la corrida a un JSON que un seed de uP1 puede cargar sin ids locales de contexto."""

from __future__ import annotations

import json
import shutil

import pytest

from indexador import indexar
from indexador.exportar import ErrorExportacion, exportar, main


@pytest.fixture
def corrida(carpeta_lote, tmp_path):
    return indexar(carpeta_lote, tmp_path / "salida").carpeta


def _todas_las_claves(valor):
    if isinstance(valor, dict):
        for clave, hijo in valor.items():
            yield clave
            yield from _todas_las_claves(hijo)
    elif isinstance(valor, list):
        for hijo in valor:
            yield from _todas_las_claves(hijo)


def test_conserva_cada_objeto_de_la_corrida(corrida, carpeta_lote):
    datos = exportar(corrida, carpeta_lote)
    for clave, archivo in [("learningElements", "learning_elements.json"), ("catalogFiles", "catalog_files.json"),
                           ("usages", "usages.json"), ("backings", "backings.json"), ("provenance", "provenance.json")]:
        original = json.loads((corrida / "objetos" / archivo).read_text(encoding="utf-8"))
        assert len(datos[clave]) == len(original), clave


def test_quita_los_ids_de_contexto_y_deja_llaves_naturales(corrida, carpeta_lote):
    datos = exportar(corrida, carpeta_lote)
    claves = set(_todas_las_claves(datos))
    assert not claves & {"id", "courseId", "offeringId", "learningOutcomeId", "learningElementId", "entityId"}
    codigos = {ra["code"] for ra in datos["resultadosAprendizaje"]}
    assert {b["learningOutcomeCode"] for b in datos["backings"]} <= codigos
    assert all(e["extractedTextUrl"] is None for e in datos["learningElements"])


def test_todas_las_referencias_resuelven(corrida, carpeta_lote):
    datos = exportar(corrida, carpeta_lote)
    elementos = {e["ref"] for e in datos["learningElements"]}
    for clave in ("catalogFiles", "usages", "backings"):
        for fila in datos[clave]:
            assert fila["learningElementRef"] is None or fila["learningElementRef"] in elementos
            assert fila["learningElementRef"] is None or fila["existingElementContentHash"] is None
    objetos = elementos | {f["ref"] for k in ("catalogFiles", "usages", "backings") for f in datos[k]}
    assert {p["entityRef"] for p in datos["provenance"]} <= objetos


def test_un_elemento_que_ya_estaba_en_el_catalogo_se_nombra_por_su_hash(corrida, carpeta_lote):
    datos = exportar(corrida, carpeta_lote)
    conocidos = {e["contentHash"] for e in json.loads((carpeta_lote / "contexto" / "catalogo.json").read_text(encoding="utf-8"))["elementos"]}
    vinculados = [c for c in datos["catalogFiles"] if c["existingElementContentHash"]]
    assert vinculados, "el lote de ejemplo tiene archivos que se vinculan a elementos existentes"
    assert {c["existingElementContentHash"] for c in vinculados} <= conocidos


def test_otro_lote_no_se_mezcla_con_la_corrida(corrida, carpeta_lote, tmp_path):
    otro = tmp_path / "otro-lote"
    shutil.copytree(carpeta_lote, otro)
    for nombre in ("lote.json", "contexto/curso.json"):
        ruta = otro / nombre
        ruta.write_text(ruta.read_text(encoding="utf-8").replace('"off-', '"off-otro-'), encoding="utf-8")
    with pytest.raises(ErrorExportacion, match="curso dictado"):
        exportar(corrida, otro)


def test_la_terminal_escribe_el_archivo(corrida, carpeta_lote, tmp_path):
    destino = tmp_path / "seed" / "datos.json"
    assert main(["--corrida", str(corrida), "--entrada", str(carpeta_lote), "--salida", str(destino)]) == 0
    assert json.loads(destino.read_text(encoding="utf-8"))["formato"] == "indexador-catalogo/exportacion@1"
