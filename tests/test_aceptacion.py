"""Los cuatro criterios de aceptación del ticket, sobre el lote de ejemplo en modo simulado."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from indexador import indexar
from indexador.esquemas import salida

RAIZ_PAQUETE = Path(__file__).resolve().parent.parent / "indexador"
OBJETOS = {
    "catalog_files.json": salida.CatalogFile,
    "learning_elements.json": salida.LearningElement,
    "backings.json": salida.Backing,
    "usages.json": salida.Usage,
    "provenance.json": salida.Provenance,
}


@pytest.fixture
def corrida(carpeta_lote, tmp_path):
    resultado = indexar(carpeta_lote, tmp_path)
    objetos = {
        nombre: [modelo.model_validate(f) for f in json.loads((resultado.carpeta / "objetos" / nombre).read_text(encoding="utf-8"))]
        for nombre, modelo in OBJETOS.items()
    }
    return resultado, objetos


# Criterio 1: aislado.
def test_el_paquete_no_importa_nada_de_up1():
    for archivo in RAIZ_PAQUETE.rglob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        assert "import up1" not in texto and "from up1" not in texto, archivo


# Criterio 2: entradas y salidas en archivos.
def test_las_salidas_validan_contra_los_esquemas(corrida):
    resultado, objetos = corrida
    assert all(objetos.values()), "cada archivo de objetos tiene filas"
    assert json.loads((resultado.carpeta / "reporte.json").read_text(encoding="utf-8"))["runId"] == resultado.runId


# Criterio 3: metadata y objetos completos.
def test_cada_elemento_nuevo_tiene_su_metadata_y_su_markdown(corrida):
    resultado, objetos = corrida
    elementos = objetos["learning_elements.json"]
    assert len(elementos) == 9
    for elemento in elementos:
        assert elemento.metadataStatus, elemento.id
        assert elemento.cognitiveLevel and elemento.knowledgeType and elemento.keywords
        assert (elemento.validityStatus, elemento.rights, elemento.ingestionStatus) == ("Valid", "Institution", "Extracted")
        assert not elemento.professorReviewed and elemento.publishedById is None
        ruta = resultado.carpeta / elemento.extractedTextUrl
        _, cabecera, cuerpo = ruta.read_text(encoding="utf-8").split("---\n", 2)
        assert yaml.safe_load(cabecera)["learningElementId"] == elemento.id
        assert cuerpo.strip()


def test_un_elemento_muchos_usos(corrida):
    _, objetos = corrida
    usos = [u for u in objetos["usages.json"] if u.id in {"us-4542265", "us-sim-0001"}]
    assert len({u.learningElementId for u in usos}) == 1
    assert {(u.weekOrUnit, u.order) for u in usos} == {("Presentación del curso", 1), ("Reto 1", 5)}


def test_referencias_consistentes(corrida):
    _, objetos = corrida
    elementos = {e.id for e in objetos["learning_elements.json"]} | {"le-existente-metodologia"}
    for archivo in objetos["catalog_files.json"]:
        if archivo.detectionExtractionStatus == "Extracted":
            assert archivo.learningElementId in elementos and archivo.identificationMethod == "ExactHash"
    for uso in objetos["usages.json"]:
        assert uso.learningElementId in elementos
    for backing in objetos["backings.json"]:
        assert backing.learningElementId in elementos
        assert backing.learningOutcomeId in {"ra-01", "ra-02", "ra-03"}


def test_nada_nace_validado(corrida):
    _, objetos = corrida
    assert all(b.status == "Proposed" and b.validatedById is None for b in objetos["backings.json"])
    assert all(u.usageCharacter == "Complementary" and not u.sequencingReviewed for u in objetos["usages.json"])


def test_cada_campo_del_agente_tiene_su_provenance(corrida):
    _, objetos = corrida
    registrados = {(p.entityId, p.fieldName): p for p in objetos["provenance.json"]}
    for elemento in objetos["learning_elements.json"]:
        for campo in ("descriptiveTitle", "description", "keywords", "cognitiveLevel", "knowledgeType", "language", "estimatedTime"):
            p = registrados[(elemento.id, campo)]
            assert p.origin == "AiAgent" and p.configVersion and "simulado@1" in p.agentIdentifier
    for uso in objetos["usages.json"]:
        assert registrados[(uso.id, "weekOrUnit")].origin == "Lms"
    for backing in objetos["backings.json"]:
        assert registrados[(backing.id, "character")].origin == "AiAgent"
    entidades = {o.id for lista in objetos.values() for o in lista if not isinstance(o, salida.Provenance)}
    assert all(p.entityId in entidades for p in objetos["provenance.json"])


def test_el_reporte_cuenta_lo_que_se_construyo(corrida):
    resultado, objetos = corrida
    t = resultado.reporte.totales
    assert (t.archivosProcesados, t.archivosVinculados, t.archivosIlegibles) == (10, 1, 3)
    assert t.learningElements == len(objetos["learning_elements.json"])
    assert t.backings == len(objetos["backings.json"]) == sum(t.backingsPorCaracter.values())
    assert t.provenance == len(objetos["provenance.json"])
    con_respaldo = [f for f in resultado.reporte.archivos if any(r.backingId for r in f.respaldos)]
    assert con_respaldo and all(r.razon for f in con_respaldo for r in f.respaldos)


# Criterio 4: un único llamado.
def test_dos_corridas_dan_los_mismos_objetos(carpeta_lote, tmp_path):
    def contenido(resultado):
        filas = json.loads((resultado.carpeta / "objetos" / "learning_elements.json").read_text(encoding="utf-8"))
        return filas

    assert contenido(indexar(carpeta_lote, tmp_path)) == contenido(indexar(carpeta_lote, tmp_path))
