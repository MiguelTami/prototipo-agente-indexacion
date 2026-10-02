"""Reglas de validación de los modelos de entrada."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from indexador.esquemas.entrada import ArchivoEntrada, Lote


def _archivo(**cambios):
    base = {
        "sourceIdentifier": "1",
        "tituloLms": "Archivo",
        "fileType": "Pdf",
        "modulo": "Reto 1",
        "orden": 1,
        "markdownPath": "archivos/a.md",
        "core": {"filename": "a.pdf", "contentHash": "x", "markdownStatus": "ok"},
    }
    base.update(cambios)
    return base


def test_estado_ok_exige_markdown():
    with pytest.raises(ValidationError, match="exige markdownPath"):
        ArchivoEntrada.model_validate(_archivo(markdownPath=None))


def test_estado_failed_no_trae_markdown():
    core = {"filename": "a.pdf", "contentHash": "x", "markdownStatus": "failed", "markdownWarning": "ilegible"}
    with pytest.raises(ValidationError, match="no trae markdown"):
        ArchivoEntrada.model_validate(_archivo(core=core))


def test_sin_markdown_exige_advertencia_del_core():
    core = {"filename": "a.pdf", "contentHash": "x", "markdownStatus": "unsupported"}
    with pytest.raises(ValidationError, match="siempre advierte"):
        ArchivoEntrada.model_validate(_archivo(markdownPath=None, core=core))


def test_file_type_fuera_del_enum_del_mod():
    with pytest.raises(ValidationError):
        ArchivoEntrada.model_validate(_archivo(fileType="Html"))


def test_identificadores_repetidos():
    lote = {
        "descripcion": "x",
        "tenant": "TEST",
        "lms": "Brightspace",
        "offeringId": "off-1",
        "archivos": [_archivo(), _archivo()],
    }
    with pytest.raises(ValidationError, match="repetido"):
        Lote.model_validate(lote)
