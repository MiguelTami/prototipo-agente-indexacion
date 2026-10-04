"""Un archivo ilegible es un resultado con su motivo, nunca un error ni un silencio."""

from __future__ import annotations

import pytest

from indexador import indexar
from indexador.esquemas.entrada import ArchivoEntrada, cargar_entrada
from indexador.legibilidad import MOTIVOS_DEL_CORE, caracteres_utiles, evaluar

ILEGIBLES = {"4542267", "4542281", "sim-0002"}


def _archivo(carpeta_lote, source_identifier: str) -> ArchivoEntrada:
    return next(a for a in cargar_entrada(carpeta_lote).lote.archivos if a.sourceIdentifier == source_identifier)


def test_los_encabezados_de_pagina_no_cuentan_como_texto():
    assert caracteres_utiles("## Página 1\n\n\n## Página 2\n") == 0
    assert caracteres_utiles("## Página 1\n\nHola mundo") == len("Holamundo")


@pytest.mark.parametrize("estado", sorted(MOTIVOS_DEL_CORE))
def test_cada_estado_del_core_sin_markdown_es_ilegible(carpeta_lote, estado):
    archivo = _archivo(carpeta_lote, "4542281").model_copy(deep=True)
    archivo.core.markdownStatus = estado
    resultado = evaluar(archivo, carpeta_lote, min_caracteres=100)
    assert not resultado.legible
    assert resultado.motivo == MOTIVOS_DEL_CORE[estado]
    assert any("Aviso del core" in a for a in resultado.advertencias)


def test_escaneo_sin_texto_es_ilegible(carpeta_lote):
    resultado = evaluar(_archivo(carpeta_lote, "sim-0002"), carpeta_lote, min_caracteres=100)
    assert not resultado.legible
    assert "0 caracteres" in resultado.motivo


def test_el_umbral_es_configurable(carpeta_lote):
    archivo = _archivo(carpeta_lote, "4542280")  # Referencias reto 2, el texto más corto del lote
    assert evaluar(archivo, carpeta_lote, min_caracteres=100).legible
    assert not evaluar(archivo, carpeta_lote, min_caracteres=10_000).legible


def test_truncado_es_legible_con_advertencia(carpeta_lote):
    resultado = evaluar(_archivo(carpeta_lote, "4542275"), carpeta_lote, min_caracteres=100)
    assert resultado.legible
    assert resultado.markdown
    assert any("truncó" in a for a in resultado.advertencias)


def test_la_corrida_termina_y_reporta_los_ilegibles(carpeta_lote, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path)
    reporte = resultado.reporte

    ilegibles = {f.sourceIdentifier: f for f in reporte.archivos if f.estado == "ilegible"}
    assert set(ilegibles) == ILEGIBLES
    assert all(f.motivo for f in ilegibles.values())
    assert all(f.pasos == ["revisar_legibilidad", "marcar_ilegible", "armar_objetos"] for f in ilegibles.values())
    assert reporte.totales.archivosIlegibles == 3

    texto = (resultado.carpeta / "reporte.md").read_text(encoding="utf-8")
    assert all(f.motivo in texto for f in ilegibles.values())


def test_cada_ilegible_sale_como_catalog_file_unreadable(carpeta_lote, tmp_path):
    objetos = indexar(carpeta_lote, tmp_path).reporte
    archivos = {f.sourceIdentifier: f for f in objetos.archivos}
    for source_identifier in ILEGIBLES:
        assert archivos[source_identifier].objetos == {"catalogFiles": [f"cf-{source_identifier}"]}
    assert objetos.totales.catalogFiles == 3


def test_ninguna_otra_ruta_llega_a_marcar_ilegible(carpeta_lote, tmp_path):
    reporte = indexar(carpeta_lote, tmp_path).reporte
    legibles = [f for f in reporte.archivos if f.sourceIdentifier not in ILEGIBLES]
    assert len(legibles) == 11
    assert all("marcar_ilegible" not in f.pasos for f in legibles)
    truncado = next(f for f in legibles if f.sourceIdentifier == "4542275")
    assert any("truncó" in a for a in truncado.advertencias)
