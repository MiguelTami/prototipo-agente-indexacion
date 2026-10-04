"""Un contenido repetido es un solo elemento, y un contenido conocido se vincula al existente."""

from __future__ import annotations

from indexador import indexar
from indexador.objetos import id_learning_element


def _por_id(reporte):
    return {f.sourceIdentifier: f for f in reporte.archivos}


def test_duplicado_del_lote_es_un_solo_contenido(carpeta_lote, tmp_path):
    archivos = _por_id(indexar(carpeta_lote, tmp_path).reporte)
    original, copia = archivos["4542265"], archivos["sim-0001"]
    assert original.contentHash == copia.contentHash
    assert original.pasos == copia.pasos, "los dos archivos comparten un solo recorrido"


def test_contenido_conocido_se_vincula_sin_regenerar_metadata(carpeta_lote, tmp_path):
    metodologia = _por_id(indexar(carpeta_lote, tmp_path).reporte)["4542268"]
    assert metodologia.pasos == ["revisar_legibilidad", "resolver_identidad", "armar_objetos"]
    assert any("le-existente-metodologia" in a for a in metodologia.advertencias)


def test_contenido_nuevo_va_a_generar_metadata(carpeta_lote, tmp_path):
    bienvenida = _por_id(indexar(carpeta_lote, tmp_path).reporte)["4542266"]
    assert "generar_metadata" in bienvenida.pasos
    assert "proponer_respaldos" in bienvenida.pasos


def test_id_de_elemento_estable():
    assert id_learning_element("abcdef1234567890") == "le-abcdef123456"
    assert id_learning_element("abcdef1234567890") == id_learning_element("abcdef1234567890")
