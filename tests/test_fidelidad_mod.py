"""Los esquemas de salida replican los objetos del mod (copia fijada en tests/fixtures/objetos-mod).

Si el mod cambia y el prototipo no, estos tests fallan y dicen qué campo o valor se movió.
"""

from __future__ import annotations

import json
import types
import typing
from pathlib import Path

import pytest

from indexador.esquemas import entrada, salida

FIXTURES = Path(__file__).parent / "fixtures" / "objetos-mod"

MODELOS = {
    "CatalogFile": salida.CatalogFile,
    "LearningElement": salida.LearningElement,
    "Backing": salida.Backing,
    "Usage": salida.Usage,
    "Provenance": salida.Provenance,
}

# Campos obligatorios en el mod que el prototipo deja opcionales a propósito.
# Cada uno es un hueco del modelo documentado en el plan.
EXCEPCIONES_OBLIGATORIEDAD = {
    ("CatalogFile", "learningElementId"): "un archivo ilegible no tiene elemento",
    ("CatalogFile", "identificationMethod"): "un archivo ilegible no tiene identidad resuelta",
}

TIPOS_JSON = {"string": str, "number": float, "integer": int, "boolean": bool, "array": list}


def _definicion(nombre: str) -> dict:
    return json.loads((FIXTURES / f"{nombre}.json").read_text(encoding="utf-8"))


def _sin_optional(anotacion):
    """Quita None de una unión y dice si la anotación lo admitía."""
    origen = typing.get_origin(anotacion)
    if origen in (typing.Union, types.UnionType):
        argumentos = [a for a in typing.get_args(anotacion) if a is not type(None)]
        admite_none = len(argumentos) < len(typing.get_args(anotacion))
        return (argumentos[0] if len(argumentos) == 1 else anotacion), admite_none
    return anotacion, False


def _literales(anotacion) -> set[str] | None:
    base, _ = _sin_optional(anotacion)
    if typing.get_origin(base) is typing.Literal:
        return set(typing.get_args(base))
    return None


def _tipo_python(anotacion):
    base, _ = _sin_optional(anotacion)
    if typing.get_origin(base) is typing.Literal:
        return str
    return typing.get_origin(base) or base


@pytest.mark.parametrize("nombre", MODELOS)
def test_mismos_campos_que_el_mod(nombre):
    campos_mod = set(_definicion(nombre)["properties"])
    campos_modelo = set(MODELOS[nombre].model_fields) - {"id"}
    assert campos_modelo == campos_mod, (
        f"faltan en el prototipo: {sorted(campos_mod - campos_modelo)}; "
        f"sobran: {sorted(campos_modelo - campos_mod)}"
    )


@pytest.mark.parametrize("nombre", MODELOS)
def test_mismos_valores_permitidos(nombre):
    propiedades = _definicion(nombre)["properties"]
    for campo, definicion in propiedades.items():
        if "enum" not in definicion:
            continue
        valores = _literales(MODELOS[nombre].model_fields[campo].annotation)
        assert valores == set(definicion["enum"]), f"{nombre}.{campo}"


@pytest.mark.parametrize("nombre", MODELOS)
def test_mismos_tipos(nombre):
    propiedades = _definicion(nombre)["properties"]
    for campo, definicion in propiedades.items():
        esperado = TIPOS_JSON[definicion["type"]]
        obtenido = _tipo_python(MODELOS[nombre].model_fields[campo].annotation)
        if esperado is float:
            assert obtenido in (float, int), f"{nombre}.{campo}"
        else:
            assert obtenido is esperado, f"{nombre}.{campo}: {obtenido} en vez de {esperado}"


@pytest.mark.parametrize("nombre", MODELOS)
def test_obligatorios_del_mod_nunca_vacios(nombre):
    for campo in _definicion(nombre).get("required", []):
        _, admite_none = _sin_optional(MODELOS[nombre].model_fields[campo].annotation)
        if (nombre, campo) in EXCEPCIONES_OBLIGATORIEDAD:
            assert admite_none, f"{nombre}.{campo} ya no necesita la excepción: quitarla"
        else:
            assert not admite_none, f"{nombre}.{campo} es obligatorio en el mod"


def test_valores_de_entrada_coinciden_con_el_mod():
    catalog_file = _definicion("CatalogFile")["properties"]
    assert set(typing.get_args(entrada.FileType)) == set(catalog_file["fileType"]["enum"])
    assert set(typing.get_args(entrada.SourceSystem)) == set(catalog_file["sourceSystem"]["enum"])

    bloom_ra = _definicion("rt__LearningOutcome__curricularsection")["properties"]["bloomLevel"]["enum"]
    nivel_elemento = _definicion("LearningElement")["properties"]["cognitiveLevel"]["enum"]
    assert set(typing.get_args(entrada.BloomLevel)) == set(bloom_ra) == set(nivel_elemento)
