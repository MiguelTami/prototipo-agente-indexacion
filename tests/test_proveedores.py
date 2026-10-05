"""Configuración de los proveedores reales, sin llamar a ninguno."""

from __future__ import annotations

import os

import pytest

from indexador import indexar
from indexador.config import cargar_config, cargar_env
from indexador.llm import ErrorModelo, obtener_modelo
from indexador.reintentos import con_reintentos


def _config_gemini(tmp_path, modelo="gemini-de-prueba"):
    config = cargar_config()
    config.llm.modo = "gemini"
    config.llm.modelo = modelo
    return config


def test_cargar_env_no_pisa_variables_existentes(tmp_path, monkeypatch):
    archivo = tmp_path / ".env"
    archivo.write_text("# comentario\nPRUEBA_A=desde-archivo\nPRUEBA_B='con comillas'\n", encoding="utf-8")
    monkeypatch.setenv("PRUEBA_A", "ya-estaba")
    monkeypatch.delenv("PRUEBA_B", raising=False)
    cargar_env(archivo)
    assert os.environ["PRUEBA_A"] == "ya-estaba"
    assert os.environ["PRUEBA_B"] == "con comillas"


def test_gemini_sin_llave_falla_antes_de_crear_la_salida(carpeta_lote, tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # sin .env
    with pytest.raises(ErrorModelo, match="GOOGLE_API_KEY"):
        indexar(carpeta_lote, tmp_path / "salida", _config_gemini(tmp_path))
    assert not (tmp_path / "salida").exists()


def test_gemini_sin_modelo_falla_con_mensaje_claro(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    with pytest.raises(ErrorModelo, match="llm.modelo"):
        obtener_modelo(_config_gemini(tmp_path, modelo=None))


def test_gemini_con_llave_construye_el_modelo(tmp_path, monkeypatch):
    pytest.importorskip("langchain_google_genai")
    monkeypatch.setenv("GOOGLE_API_KEY", "llave-de-prueba")
    modelo = obtener_modelo(_config_gemini(tmp_path, modelo="gemini-construccion"))
    assert modelo.identificador == "gemini/gemini-construccion"


def test_la_espera_entre_reintentos_se_duplica(monkeypatch):
    esperas = []
    monkeypatch.setattr("indexador.reintentos.time.sleep", esperas.append)

    def siempre_falla():
        raise ErrorModelo("429 límite de solicitudes")

    valor, errores = con_reintentos(siempre_falla, reintentos=3, espera=10)
    assert valor is None and len(errores) == 4
    assert esperas == [10, 20, 40]


def test_la_configuracion_de_gemini_del_repo_es_valida():
    from pathlib import Path

    config = cargar_config(Path(__file__).resolve().parent.parent / "config.gemini.yaml")
    assert config.llm.modo == "gemini" and config.llm.modelo
    assert config.llm.maxConcurrencia <= 2 and config.llm.esperaReintentoSegundos > 0
