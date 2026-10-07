"""El modelo simulado es determinista y un fallo del modelo nunca corta la corrida."""

from __future__ import annotations

import json

import pytest

from indexador import indexar
from indexador.config import cargar_config
from indexador.esquemas.entrada import cargar_entrada
from indexador.llm import (
    ErrorModelo,
    JuicioRespaldo,
    JuiciosRespaldo,
    ModeloSimulado,
    Respuesta,
    obtener_modelo,
)
from indexador.reintentos import con_reintentos


def _archivo_y_markdown(carpeta_lote, source_identifier):
    entrada = cargar_entrada(carpeta_lote)
    archivo = next(a for a in entrada.lote.archivos if a.sourceIdentifier == source_identifier)
    return entrada, archivo, (carpeta_lote / archivo.markdownPath).read_text(encoding="utf-8")


def test_el_simulado_es_determinista(carpeta_lote):
    entrada, archivo, markdown = _archivo_y_markdown(carpeta_lote, "4542273")
    modelo = ModeloSimulado()
    primera = modelo.generar_metadata(markdown, archivo, entrada.contexto).valor
    segunda = modelo.generar_metadata(markdown, archivo, entrada.contexto).valor
    assert primera == segunda
    assert primera.language == "es"


def test_el_simulado_identifica_autores_explicitos(carpeta_lote):
    entrada, archivo, markdown = _archivo_y_markdown(carpeta_lote, "4542272")
    metadata = ModeloSimulado().generar_metadata(markdown, archivo, entrada.contexto).valor
    assert metadata.identifiedAuthors == ["Ana María Restrepo Gil", "Julián Ortega Pardo", "Carolina Vélez Ríos"]


def test_el_simulado_juzga_todos_los_ra(carpeta_lote):
    entrada, archivo, markdown = _archivo_y_markdown(carpeta_lote, "4542274")
    modelo = ModeloSimulado()
    metadata = modelo.generar_metadata(markdown, archivo, entrada.contexto).valor
    juicios = modelo.juzgar_respaldos(markdown, metadata, entrada.contexto).valor.juicios
    assert [j.codigoRA for j in juicios] == ["RA-01", "RA-02", "RA-03"]
    ra02 = juicios[1]
    assert ra02.aporta and ra02.caracter in {"Develops", "Evaluates", "Both"}


def test_reintentos_devuelven_el_primer_exito():
    intentos = iter([ErrorModelo("timeout"), "ok"])

    def llamada():
        valor = next(intentos)
        if isinstance(valor, Exception):
            raise valor
        return valor

    valor, errores = con_reintentos(llamada, reintentos=2)
    assert valor == "ok" and errores == ["timeout"]


def test_bedrock_sin_modelo_configurado_falla_con_un_mensaje_claro():
    config = cargar_config()
    config.llm.modo = "bedrock"
    config.llm.modelo = None
    with pytest.raises(ErrorModelo, match="llm.modelo"):
        obtener_modelo(config)


class _ModeloQueFalla(ModeloSimulado):
    identificador = "falla@1"

    def generar_metadata(self, markdown, archivo, contexto):
        raise ErrorModelo("respuesta no válida")


class _ModeloConRaAjeno(ModeloSimulado):
    identificador = "ajeno@1"

    def juzgar_respaldos(self, markdown, metadata, contexto):
        juicio = JuicioRespaldo(codigoRA="RA-99", aporta=True, caracter="Develops", confianza=0.9, razon="x")
        return Respuesta(JuiciosRespaldo(juicios=[juicio]))


def test_si_el_modelo_falla_el_contenido_sale_ilegible_y_la_corrida_sigue(carpeta_lote, tmp_path, monkeypatch):
    monkeypatch.setattr("indexador.nodos.generar_metadata.obtener_modelo", lambda config: _ModeloQueFalla())
    resultado = indexar(carpeta_lote, tmp_path)
    reporte = resultado.reporte

    fallidos = [f for f in reporte.archivos if f.pasos[-2:] == ["marcar_ilegible", "armar_objetos"] and "generar_metadata" in f.pasos]
    assert len(fallidos) == 10, "los 10 archivos con elemento nuevo pasan por el modelo"
    assert all(f.estado == "ilegible" and "3 intentos" in f.motivo for f in fallidos)
    # LAB-40: cada contenido nuevo sale igual, como elemento sin describir. Ninguno trae metadata.
    elementos = json.loads((resultado.carpeta / "objetos" / "learning_elements.json").read_text(encoding="utf-8"))
    assert reporte.totales.learningElements == len(elementos) == 12
    assert all(e["ingestionStatus"] == "Detected" and e["metadataStatus"] is False for e in elementos)


def test_los_ra_ajenos_al_curso_se_descartan(carpeta_lote, tmp_path, monkeypatch):
    monkeypatch.setattr("indexador.nodos.proponer_respaldos.obtener_modelo", lambda config: _ModeloConRaAjeno())
    reporte = indexar(carpeta_lote, tmp_path).reporte

    assert reporte.totales.backings == 0
    bienvenida = next(f for f in reporte.archivos if f.sourceIdentifier == "4542266")
    assert any("RA-99" in a for a in bienvenida.advertencias)
