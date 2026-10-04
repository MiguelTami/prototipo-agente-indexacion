"""La traza muestra cada nodo y la evaluación detecta acuerdos y desacuerdos."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from indexador import indexar
from indexador.esquemas.esperado import RespuestasEsperadas, cargar_esperado
from indexador.evaluacion import escribir_evaluacion, evaluar


@pytest.fixture
def esperado(carpeta_lote) -> RespuestasEsperadas:
    return cargar_esperado(carpeta_lote / "esperado.json")


def test_sin_trazar_no_hay_traza(carpeta_lote, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path)
    assert not (resultado.carpeta / "traza.json").exists()


def test_la_traza_muestra_lo_que_devolvio_cada_nodo(carpeta_lote, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path, trazar=True)
    traza = json.loads((resultado.carpeta / "traza.json").read_text(encoding="utf-8"))

    assert len(traza) == 13, "una entrada por contenido único"
    programa = traza[0]
    assert programa["sourceIdentifiers"] == ["4542265", "sim-0001"]
    nodos = [p["nodo"] for p in programa["pasos"]]
    assert nodos == ["revisar_legibilidad", "resolver_identidad", "generar_metadata", "proponer_respaldos", "armar_objetos"]
    salidas = {p["nodo"]: p["salida"] for p in programa["pasos"]}
    assert salidas["revisar_legibilidad"]["markdown"].endswith("caracteres>"), "el markdown se resume"
    assert salidas["generar_metadata"]["metadata"]["language"] == "es"
    assert len(salidas["proponer_respaldos"]["juicios"]) == 3
    assert salidas["armar_objetos"]["objetos"]["usages"] == ["us-4542265", "us-sim-0001"]
    assert "Programa de curso" in (resultado.carpeta / "traza.md").read_text(encoding="utf-8")


def test_las_respuestas_esperadas_cubren_todo_el_lote(carpeta_lote, esperado):
    from indexador.esquemas.entrada import cargar_entrada

    ids = {a.sourceIdentifier for a in cargar_entrada(carpeta_lote).lote.archivos}
    assert set(esperado.archivos) == ids
    codigos = {"RA-01", "RA-02", "RA-03"}
    for archivo in esperado.archivos.values():
        if archivo.elemento:
            assert set(archivo.elemento.respaldos) == codigos


def test_la_evaluacion_del_lote_simulado(carpeta_lote, esperado, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path)
    evaluacion = evaluar(resultado.carpeta, esperado)

    assert evaluacion.campos["estado"].aciertos == evaluacion.campos["estado"].total == 14
    assert evaluacion.campos["mismoElemento"].porcentaje == 100.0
    assert evaluacion.campos["cognitiveLevel"].total == 9
    assert evaluacion.campos["respaldo.aporta"].total > 0
    assert evaluacion.sinRespuestaEsperada == []

    escribir_evaluacion(evaluacion, resultado.carpeta)
    datos = json.loads((resultado.carpeta / "evaluacion.json").read_text(encoding="utf-8"))
    assert datos["campos"]["estado"]["porcentaje"] == 100.0
    assert "Acuerdo por campo" in (resultado.carpeta / "evaluacion.md").read_text(encoding="utf-8")


def test_un_desacuerdo_se_detecta(carpeta_lote, esperado, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path)
    modificado = esperado.model_copy(deep=True)
    modificado.archivos["4542267"].estado = "procesado"
    modificado.archivos["4542272"].elemento.identifiedAuthors = ["Otra Persona"]

    evaluacion = evaluar(resultado.carpeta, modificado)
    campos = {(d.sourceIdentifier, d.campo) for d in evaluacion.desacuerdos}
    assert ("4542267", "estado") in campos
    assert ("4542272", "identifiedAuthors") in campos


def test_respaldo_ambiguo_no_cuenta(carpeta_lote, esperado, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path)
    base = evaluar(resultado.carpeta, esperado).campos["respaldo.aporta"].total
    modificado = esperado.model_copy(deep=True)
    modificado.archivos["4542273"].elemento.respaldos["RA-02"].aporta = None
    assert evaluar(resultado.carpeta, modificado).campos["respaldo.aporta"].total == base - 1


def test_la_terminal_traza_y_evalua(carpeta_lote, tmp_path):
    salida = subprocess.run(
        [sys.executable, "-m", "indexador", "--entrada", str(carpeta_lote), "--salida", str(tmp_path), "--trazar", "--evaluar"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert "=== 4542265, sim-0001 · Programa de curso" in salida.stdout
    assert "metadata.cognitiveLevel" in salida.stdout
    assert "Acuerdo con las respuestas esperadas" in salida.stdout
    carpeta = next(p for p in tmp_path.iterdir() if p.is_dir())
    assert (carpeta / "evaluacion.md").is_file() and (carpeta / "traza.md").is_file()
